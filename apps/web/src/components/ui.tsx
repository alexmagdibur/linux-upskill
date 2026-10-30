import type { ButtonHTMLAttributes, ReactNode } from "react";

import { friendlyMessage } from "../api/client";
import type { Difficulty, Mode, SessionStatus } from "../types/api";

type Variant = "primary" | "secondary" | "danger" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-emerald-500 text-slate-950 hover:bg-emerald-400 disabled:bg-emerald-900 disabled:text-slate-500",
  secondary: "bg-slate-800 text-slate-100 hover:bg-slate-700 disabled:text-slate-500",
  danger: "bg-rose-600 text-white hover:bg-rose-500 disabled:bg-rose-950 disabled:text-slate-500",
  ghost: "text-slate-300 hover:bg-slate-800 disabled:text-slate-600",
};

export function Button({
  variant = "primary",
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      {...rest}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
    />
  );
}

export function Spinner({ label = "Загрузка…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-emerald-400" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div role="alert" className="rounded-md border border-rose-800 bg-rose-950/60 px-4 py-3 text-sm text-rose-200">
      {friendlyMessage(error)}
    </div>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-xl border border-slate-800 bg-slate-900/60 p-5 ${className}`}>{children}</div>;
}

const MODE_STYLE: Record<Mode, string> = {
  learn: "bg-sky-900/60 text-sky-200",
  practice: "bg-violet-900/60 text-violet-200",
  incident: "bg-rose-900/60 text-rose-200",
};
const MODE_LABEL: Record<Mode, string> = { learn: "Learn", practice: "Practice", incident: "Incident" };
export function ModeBadge({ mode }: { mode: Mode }) {
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${MODE_STYLE[mode]}`}>{MODE_LABEL[mode]}</span>;
}

const DIFF_LABEL: Record<Difficulty, string> = { beginner: "Начальный", junior: "Junior", middle: "Middle" };
export function DifficultyBadge({ difficulty }: { difficulty: Difficulty }) {
  return <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs text-slate-300">{DIFF_LABEL[difficulty]}</span>;
}

export const STATUS_LABEL: Record<SessionStatus, string> = {
  CREATED: "Создаётся",
  PROVISIONING: "Подготовка окружения…",
  READY: "Готово",
  RUNNING: "Идёт работа",
  VALIDATING: "Проверка…",
  COMPLETED: "Пройдено",
  FAILED: "Ошибка запуска",
  STOPPING: "Останавливается…",
  STOPPED: "Остановлено",
  EXPIRED: "Время вышло",
};

export function StatusChip({ status }: { status: SessionStatus }) {
  const tone =
    status === "COMPLETED"
      ? "bg-emerald-900/60 text-emerald-200"
      : status === "FAILED" || status === "EXPIRED"
        ? "bg-rose-900/60 text-rose-200"
        : status === "READY" || status === "RUNNING"
          ? "bg-sky-900/60 text-sky-200"
          : "bg-slate-800 text-slate-300";
  return (
    <span data-testid="session-status" data-status={status} className={`rounded-full px-3 py-1 text-xs font-semibold ${tone}`}>
      {STATUS_LABEL[status]}
    </span>
  );
}

export function PageTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-bold tracking-tight">{children}</h1>
      {sub && <p className="mt-1 text-slate-400">{sub}</p>}
    </header>
  );
}
