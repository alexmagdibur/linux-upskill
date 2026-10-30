import { useState } from "react";
import { Link } from "react-router-dom";

import { Button, Card, ErrorBanner, PageTitle, Spinner, STATUS_LABEL } from "../components/ui";
import { useAuth } from "../features/auth/useAuth";
import { useProgress, useSessionHistory } from "../features/catalog/hooks";

const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleString("ru-RU") : "—");

export function Profile() {
  const { user } = useAuth();
  const progress = useProgress();
  const [limit, setLimit] = useState(10);
  const history = useSessionHistory(limit);

  return (
    <div>
      <PageTitle sub={user?.email}>Профиль и прогресс</PageTitle>
      {progress.isLoading && <Spinner />}
      <ErrorBanner error={progress.error ?? history.error} />
      {progress.data && (
        <Card className="mb-8">
          <div className="flex flex-wrap gap-8">
            <div><div className="text-sm text-slate-400">Всего XP</div><div className="text-3xl font-bold text-emerald-300">{progress.data.total_xp}</div></div>
            <div><div className="text-sm text-slate-400">Пройдено</div><div className="text-3xl font-bold">{progress.data.completed_labs} / {progress.data.labs_total}</div></div>
          </div>
        </Card>
      )}
      <h2 className="mb-3 text-lg font-semibold">Лучшие результаты</h2>
      {progress.data && progress.data.items.length === 0 && <p className="text-slate-400">Пока нет завершённых попыток.</p>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-left text-sm">
          <thead className="text-slate-400"><tr><th className="py-2 pr-4">Лаборатория</th><th className="pr-4">Лучший балл</th><th className="pr-4">Попыток</th><th>Пройдена</th></tr></thead>
          <tbody>
            {progress.data?.items.map((p) => (
              <tr key={p.lab_id} className="border-t border-slate-800">
                <td className="py-2 pr-4"><Link className="text-emerald-300 underline" to={`/labs/${p.lab_id}`}>{p.title}</Link></td>
                <td className="pr-4">{p.best_score}%</td><td className="pr-4">{p.attempts_count}</td><td>{fmt(p.completed_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h2 className="mb-3 mt-8 text-lg font-semibold">История сессий</h2>
      <ul className="space-y-2">
        {history.data?.items.map((s) => (
          <li key={s.session_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-2 text-sm">
            <span>{s.lab_title}</span><span className="text-slate-400">{STATUS_LABEL[s.status]} · {fmt(s.created_at)}</span>
          </li>
        ))}
      </ul>
      {history.data && history.data.total > limit && <Button variant="secondary" className="mt-3" onClick={() => setLimit((l) => l + 10)}>Показать ещё</Button>}
    </div>
  );
}
