import { Link } from "react-router-dom";

import { Card, ErrorBanner, PageTitle, Spinner, STATUS_LABEL } from "../components/ui";
import { useAuth } from "../features/auth/useAuth";
import { useLabs, useProgress, useSessionHistory } from "../features/catalog/hooks";

const ACTIVE = new Set(["PROVISIONING", "READY", "RUNNING", "VALIDATING"]);

export function Dashboard() {
  const { user } = useAuth();
  const progress = useProgress();
  const todo = useLabs({ completed: "false", availability: "available" });
  const history = useSessionHistory(5);
  const active = history.data?.items.find((s) => ACTIVE.has(s.status));
  const next = todo.data?.items[0];

  return (
    <div>
      <PageTitle sub="Ваш прогресс и что делать дальше.">Привет, {user?.display_name ?? user?.email}!</PageTitle>
      {progress.isLoading && <Spinner />}
      <ErrorBanner error={progress.error} />
      {progress.data && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><div className="text-sm text-slate-400">Опыт</div><div data-testid="dash-xp" className="mt-1 text-3xl font-bold text-emerald-300">{progress.data.total_xp} XP</div></Card>
          <Card><div className="text-sm text-slate-400">Пройдено лабораторий</div><div className="mt-1 text-3xl font-bold">{progress.data.completed_labs} / {progress.data.labs_total}</div></Card>
          <Card>
            <div className="text-sm text-slate-400">Продолжить</div>
            {active ? (
              <Link className="mt-1 block font-semibold text-emerald-300 underline" to={`/workspace/${active.session_id}`}>Активная лаборатория: {active.lab_title}</Link>
            ) : next ? (
              <Link className="mt-1 block font-semibold text-emerald-300 underline" to={`/labs/${next.id}`}>{next.title}</Link>
            ) : (
              <div className="mt-1 text-slate-300">Все лаборатории пройдены 🎉</div>
            )}
          </Card>
        </div>
      )}
      <h2 className="mb-3 mt-8 text-lg font-semibold">Последние попытки</h2>
      {progress.data && progress.data.recent_attempts.length === 0 && <p className="text-slate-400">Попыток пока нет — <Link className="text-emerald-300 underline" to="/catalog">выберите лабораторию</Link>.</p>}
      <ul className="space-y-2">
        {progress.data?.recent_attempts.map((a) => (
          <li key={a.attempt_id} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm">
            <span>{a.lab_id ?? "—"}</span>
            <span className={a.passed ? "text-emerald-300" : "text-slate-400"}>{a.status === "ERROR" ? "ошибка проверки" : a.passed ? "пройдено" : "не пройдено"}{a.score != null ? ` · ${a.score}%` : ""}</span>
          </li>
        ))}
      </ul>
      {history.data && history.data.items.length > 0 && (
        <p className="mt-6 text-xs text-slate-500">Последняя сессия: {STATUS_LABEL[history.data.items[0]!.status]}</p>
      )}
    </div>
  );
}
