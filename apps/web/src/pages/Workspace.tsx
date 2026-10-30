import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Markdown } from "../components/Markdown";
import { Button, Card, ErrorBanner, ModeBadge, Spinner, StatusChip } from "../components/ui";
import { useNextHint, useResetSession, useSession, useStopSession, useValidate } from "../features/laboratory/hooks";
import { Terminal } from "../features/terminal/Terminal";
import type { ValidationResult } from "../types/api";

const TERMINAL_STATES = new Set(["READY", "RUNNING", "VALIDATING"]);
const ENDED = new Set(["COMPLETED", "FAILED", "STOPPED", "EXPIRED", "STOPPING"]);

function useCountdown(expiresAt: string | undefined): string {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!expiresAt) return "";
  const left = Math.max(0, Math.floor((new Date(expiresAt).getTime() - now) / 1000));
  return `${String(Math.floor(left / 60)).padStart(2, "0")}:${String(left % 60).padStart(2, "0")}`;
}

export function Workspace() {
  const { sessionId = "" } = useParams();
  const nav = useNavigate();
  const session = useSession(sessionId);
  const validate = useValidate(sessionId);
  const stop = useStopSession(sessionId);
  const reset = useResetSession(sessionId);
  const hint = useNextHint(sessionId);
  const [tab, setTab] = useState<"task" | "terminal">("task");
  const [result, setResult] = useState<ValidationResult | null>(null);
  const left = useCountdown(session.data?.expires_at);

  if (session.isLoading) return <Spinner label="Загрузка лаборатории…" />;
  if (session.error || !session.data) return <ErrorBanner error={session.error} />;
  const s = session.data;
  const canUse = s.status === "READY" || s.status === "RUNNING";
  const ended = ENDED.has(s.status);

  async function check() {
    setResult(null);
    const r = await validate.mutateAsync().catch(() => null);
    if (!r) return;
    setResult(r);
    if (r.passed) nav(`/result/${sessionId}/${r.attempt_id}`);
  }

  async function doReset() {
    if (!window.confirm("Начать лабораторию заново? Текущее окружение будет удалено.")) return;
    const n = await reset.mutateAsync().catch(() => null);
    if (n) {
      setResult(null);
      nav(`/workspace/${n.session_id}`, { replace: true });
    }
  }

  async function doStop() {
    if (!window.confirm("Остановить лабораторию? Окружение будет удалено.")) return;
    await stop.mutateAsync().catch(() => null);
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] min-h-[560px] flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold">{s.lab.title}</h1>
        <ModeBadge mode={s.lab.mode} />
        <StatusChip status={s.status} />
        {!ended && left && <span className="font-mono text-sm text-slate-400" title="Оставшееся время сессии">⏱ {left}</span>}
        <div className="ml-auto flex flex-wrap gap-2">
          <Button data-testid="check" disabled={!canUse || validate.isPending} onClick={check}>
            {validate.isPending || s.status === "VALIDATING" ? "Проверка…" : "Проверить"}
          </Button>
          <Button variant="secondary" disabled={reset.isPending || s.status === "STOPPING"} onClick={doReset}>Сначала</Button>
          <Button variant="danger" disabled={ended || stop.isPending} onClick={doStop}>Остановить</Button>
        </div>
      </div>

      <div role="tablist" aria-label="Раздел" className="flex gap-2 lg:hidden">
        {(["task", "terminal"] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-semibold ${tab === t ? "bg-emerald-500 text-slate-950" : "bg-slate-800"}`}>
            {t === "task" ? "Задание" : "Терминал"}
          </button>
        ))}
      </div>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(320px,2fr)_3fr]">
        <aside className={`${tab === "task" ? "block" : "hidden"} min-h-0 space-y-4 overflow-y-auto pr-1 lg:block`} aria-label="Задание">
          <ErrorBanner error={validate.error ?? stop.error ?? reset.error ?? hint.error} />
          {s.status === "FAILED" && (
            <div role="alert" className="rounded-md border border-rose-800 bg-rose-950/60 px-4 py-3 text-sm text-rose-200">
              Не удалось подготовить окружение{s.error_code ? ` (${s.error_code})` : ""}. Нажмите «Сначала», чтобы повторить.
            </div>
          )}
          {s.status === "EXPIRED" && <div role="alert" className="rounded-md border border-amber-800 bg-amber-950/60 px-4 py-3 text-sm text-amber-200">Время сессии истекло. Нажмите «Сначала», чтобы запустить лабораторию заново.</div>}
          {(s.theory || s.prediction) && (
            <Card>
              <details>
                <summary className="cursor-pointer font-semibold">Теория и вопрос перед терминалом</summary>
                {s.theory && <div className="mt-3"><Markdown text={s.theory} /></div>}
                {s.prediction && <p className="mt-3 rounded border border-sky-900 bg-sky-950/40 p-3 text-sm text-slate-300"><strong>Перед терминалом:</strong> {s.prediction}</p>}
              </details>
            </Card>
          )}
          <Card>
            <h2 className="mb-3 font-semibold">Задание</h2>
            <Markdown text={s.task} />
            {s.criterion && <p className="mt-3 text-sm text-slate-400"><strong>Критерий успеха:</strong> {s.criterion}</p>}
          </Card>
          <Card>
            <h2 className="mb-2 font-semibold">Критерии успеха</h2>
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">{s.checks.map((c) => <li key={c}>{c}</li>)}</ul>
            <p className="mt-2 text-xs text-slate-500">Проверяется итоговое состояние системы, а не набранные команды.</p>
          </Card>
          {result && (
            <Card className={result.passed ? "border-emerald-700" : "border-amber-700"}>
              <div data-testid="check-result" aria-live="polite">
                {result.status === "ERROR" ? (
                  <p className="text-amber-200">Проверку выполнить не удалось ({result.error_code}). Повторите позже.</p>
                ) : (
                  <>
                    <p className="font-semibold">{result.passed ? "Пройдено!" : "Пока не всё готово"} · {result.score}%</p>
                    <ul className="mt-2 space-y-1 text-sm">
                      {result.checks.map((c) => (
                        <li key={c.id} className={c.passed ? "text-emerald-300" : "text-rose-300"}>{c.passed ? "✓" : "✗"} {c.message}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </Card>
          )}
          <Card>
            <h2 className="mb-2 font-semibold">Подсказки ({s.hints.length}/{s.hints_total})</h2>
            <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-300">{s.hints.map((h) => <li key={h}><Markdown text={h} /></li>)}</ol>
            {s.hints.length < s.hints_total && !ended && (
              <Button variant="secondary" className="mt-3" disabled={hint.isPending} onClick={() => hint.mutate()}>Показать подсказку</Button>
            )}
          </Card>
          <p className="text-xs text-slate-500"><Link className="underline" to="/catalog">← К каталогу</Link></p>
        </aside>

        <section className={`${tab === "terminal" ? "block" : "hidden"} relative min-h-[360px] lg:block`} aria-label="Терминал">
          {s.status === "PROVISIONING" || s.status === "CREATED" ? (
            <div className="flex h-full items-center justify-center rounded-lg border border-slate-800 bg-slate-950"><Spinner label="Подготовка окружения…" /></div>
          ) : (
            <Terminal sessionId={sessionId} enabled={TERMINAL_STATES.has(s.status)} />
          )}
        </section>
      </div>
    </div>
  );
}
