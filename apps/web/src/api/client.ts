export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

const FRIENDLY: Record<string, string> = {
  INVALID_CREDENTIALS: "Неверный email или пароль.",
  EMAIL_TAKEN: "Этот email уже зарегистрирован.",
  RATE_LIMITED: "Слишком много попыток. Подождите немного и повторите.",
  TOO_MANY_SESSIONS: "У вас уже запущено максимальное число лабораторий. Остановите одну из них.",
  CAPACITY_EXCEEDED: "Все песочницы сейчас заняты. Попробуйте через несколько минут.",
  SANDBOX_DISABLED: "Песочницы отключены на этом сервере.",
  VALIDATION_IN_PROGRESS: "Проверка уже выполняется.",
  INVALID_STATE: "Действие недоступно в текущем состоянии лаборатории.",
  SERVICE_UNAVAILABLE: "Сервис временно недоступен. Повторите позже.",
  UNAUTHORIZED: "Требуется вход в систему.",
  NOT_FOUND: "Не найдено.",
  VALIDATION_ERROR: "Проверьте введённые данные.",
};

export function friendlyMessage(err: unknown): string {
  if (err instanceof ApiError) return FRIENDLY[err.code] ?? err.message;
  return "Не удалось связаться с сервером.";
}

export function readCookie(name: string, cookie: string = document.cookie): string {
  const m = cookie.split("; ").find((c) => c.startsWith(name + "="));
  return m ? decodeURIComponent(m.slice(name.length + 1)) : "";
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const BASE = "/api/v1";

let refreshing: Promise<boolean> | null = null;
async function refreshSession(): Promise<boolean> {
  refreshing ??= fetch(`${BASE}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRF-Token": readCookie("upskill_csrf") },
  })
    .then((r) => r.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api<T>(
  path: string,
  opts: { method?: string; body?: unknown; headers?: Record<string, string>; retry?: boolean } = {},
): Promise<T> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = { ...opts.headers };
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (UNSAFE.has(method)) headers["X-CSRF-Token"] = readCookie("upskill_csrf");

  const res = await fetch(BASE + path, {
    method,
    credentials: "include",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  if (res.status === 401 && opts.retry !== false && !path.startsWith("/auth/")) {
    if (await refreshSession()) return api<T>(path, { ...opts, retry: false });
  }
  if (res.status === 204) return undefined as T;
  const data: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    const e = (data as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null)?.error;
    throw new ApiError(res.status, e?.code ?? "HTTP_ERROR", e?.message ?? `HTTP ${res.status}`, e?.details);
  }
  return data as T;
}
