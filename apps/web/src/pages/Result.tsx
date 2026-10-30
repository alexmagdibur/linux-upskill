import { Link, useNavigate, useParams } from "react-router-dom";

import { Button, Card, ErrorBanner, PageTitle, Spinner } from "../components/ui";
import { useLabs } from "../features/catalog/hooks";
import { useSession, useStartLab, useValidationResult } from "../features/laboratory/hooks";

export function Result() {
  const { sessionId = "", attemptId = "" } = useParams();
  const nav = useNavigate();
  const result = useValidationResult(sessionId, attemptId);
  const session = useSession(sessionId);
  const todo = useLabs({ completed: "false" });
  const start = useStartLab();

  if (result.isLoading) return <Spinner />;
  if (result.error || !result.data) return <ErrorBanner error={result.error} />;
  const r = result.data;
  const labId = session.data?.lab.id;
  const next = todo.data?.items.find((l) => l.id !== labId);

  return (
    <div className="max-w-2xl">
      <PageTitle sub={session.data?.lab.title}>{r.passed ? "Лаборатория пройдена 🎉" : "Результат проверки"}</PageTitle>
      <Card className={r.passed ? "border-emerald-700" : "border-amber-700"}>
        <div className="flex items-end justify-between">
          <div><div className="text-sm text-slate-400">Оценка</div><div data-testid="result-score" className="text-4xl font-bold">{r.score}%</div></div>
          <div className="text-right"><div className="text-sm text-slate-400">Награда</div>
            <div data-testid="result-xp" className="text-3xl font-bold text-emerald-300">+{r.xp_awarded} XP</div></div>
        </div>
        {r.passed && r.xp_awarded === 0 && <p className="mt-2 text-xs text-slate-500">XP начисляется только за первое прохождение лаборатории.</p>}
        <ul className="mt-5 space-y-2" aria-label="Результаты проверок">
          {r.checks.map((c) => (
            <li key={c.id} className={`flex gap-2 ${c.passed ? "text-emerald-300" : "text-rose-300"}`}><span aria-hidden>{c.passed ? "✓" : "✗"}</span>{c.message}</li>
          ))}
        </ul>
      </Card>

      <section className="mt-6" aria-label="Что дальше">
        <h2 className="mb-2 font-semibold">Что дальше</h2>
        <div className="flex flex-wrap gap-3">
          {next && (
            <Button disabled={start.isPending} onClick={async () => { const s = await start.mutateAsync(next.id).catch(() => null); if (s) nav(`/workspace/${s.session_id}`); }}>
              Следующая: {next.title}
            </Button>
          )}
          {labId && <Link to={`/labs/${labId}`} className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold hover:bg-slate-700">Пройти ещё раз</Link>}
          <Link to="/catalog" className="rounded-md bg-slate-800 px-4 py-2 text-sm font-semibold hover:bg-slate-700">К каталогу</Link>
        </div>
        <ErrorBanner error={start.error} />
      </section>
    </div>
  );
}
