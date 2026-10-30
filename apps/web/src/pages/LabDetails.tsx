import { useNavigate, useParams } from "react-router-dom";

import { Button, Card, DifficultyBadge, ErrorBanner, ModeBadge, PageTitle, Spinner } from "../components/ui";
import { useLab } from "../features/catalog/hooks";
import { useStartLab } from "../features/laboratory/hooks";

export function LabDetails() {
  const { labId = "" } = useParams();
  const nav = useNavigate();
  const lab = useLab(labId);
  const start = useStartLab();

  if (lab.isLoading) return <Spinner />;
  if (lab.error || !lab.data) return <ErrorBanner error={lab.error} />;
  const l = lab.data;

  return (
    <div className="max-w-3xl">
      <div className="mb-3 flex gap-2"><ModeBadge mode={l.mode} /><DifficultyBadge difficulty={l.difficulty} /></div>
      <PageTitle sub={l.description}>{l.title}</PageTitle>
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="font-semibold">Цели</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-300">{l.objectives.map((o) => <li key={o}>{o}</li>)}</ul>
        </Card>
        <Card>
          <h2 className="font-semibold">Навыки</h2>
          <div className="mt-2 flex flex-wrap gap-2">{l.skills.map((s) => <span key={s} className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-emerald-300">{s}</span>)}</div>
          <dl className="mt-4 space-y-1 text-sm text-slate-400">
            <div className="flex justify-between"><dt>Время</dt><dd>~{l.estimated_minutes} мин</dd></div>
            <div className="flex justify-between"><dt>Награда</dt><dd>{l.base_xp} XP (за первое прохождение)</dd></div>
            <div className="flex justify-between"><dt>Подсказок</dt><dd>{l.hints_total}</dd></div>
            {l.best_score != null && <div className="flex justify-between"><dt>Лучший результат</dt><dd>{l.best_score}%</dd></div>}
          </dl>
        </Card>
      </div>
      <div className="mt-6 space-y-3">
        <ErrorBanner error={start.error} />
        <Button
          data-testid="start-lab"
          disabled={start.isPending}
          onClick={async () => {
            const s = await start.mutateAsync(l.id).catch(() => null);
            if (s) nav(`/workspace/${s.session_id}`);
          }}
        >
          {start.isPending ? "Запуск…" : l.completed ? "Запустить снова" : "Запустить лабораторию"}
        </Button>
      </div>
    </div>
  );
}
