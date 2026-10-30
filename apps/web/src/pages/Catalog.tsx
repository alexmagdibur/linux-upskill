import { useState } from "react";
import { Link } from "react-router-dom";

import { Card, DifficultyBadge, ErrorBanner, ModeBadge, PageTitle, Spinner } from "../components/ui";
import { useLabs, type LabFilters } from "../features/catalog/hooks";
import type { LabSummary } from "../types/api";

const select = "rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm";

export function Catalog() {
  const [filters, setFilters] = useState<LabFilters>({});
  const labs = useLabs(filters);
  const set = (k: keyof LabFilters) => (e: React.ChangeEvent<HTMLSelectElement>) => setFilters((f) => ({ ...f, [k]: e.target.value }));

  const groups = new Map<string, { title: string; labs: LabSummary[] }>();
  for (const lab of labs.data?.items ?? []) {
    const g = groups.get(lab.module.slug) ?? { title: lab.module.title, labs: [] };
    g.labs.push(lab);
    groups.set(lab.module.slug, g);
  }

  return (
    <div>
      <PageTitle sub="Выберите лабораторию и запустите её в изолированной песочнице.">Каталог лабораторий</PageTitle>
      <form aria-label="Фильтры" className="mb-6 flex flex-wrap gap-3">
        <label className="text-sm text-slate-300">Режим<br />
          <select className={select} value={filters.mode ?? ""} onChange={set("mode")} aria-label="Режим">
            <option value="">Все</option><option value="learn">Learn</option><option value="practice">Practice</option><option value="incident">Incident</option>
          </select>
        </label>
        <label className="text-sm text-slate-300">Сложность<br />
          <select className={select} value={filters.difficulty ?? ""} onChange={set("difficulty")} aria-label="Сложность">
            <option value="">Любая</option><option value="beginner">Начальный</option><option value="junior">Junior</option><option value="middle">Middle</option>
          </select>
        </label>
        <label className="text-sm text-slate-300">Статус<br />
          <select className={select} value={filters.completed ?? ""} onChange={set("completed")} aria-label="Статус">
            <option value="">Все</option><option value="false">Не пройдены</option><option value="true">Пройдены</option>
          </select>
        </label>
      </form>
      {labs.isLoading && <Spinner />}
      <ErrorBanner error={labs.error} />
      {labs.data && labs.data.items.length === 0 && <p className="text-slate-400">По выбранным фильтрам ничего не найдено.</p>}
      {[...groups.entries()].map(([slug, g]) => (
        <section key={slug} className="mb-8" aria-labelledby={`m-${slug}`}>
          <h2 id={`m-${slug}`} className="mb-3 text-lg font-semibold text-slate-200">{g.title}</h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {g.labs.map((lab) => (
              <Link key={lab.id} to={`/labs/${lab.id}`} data-testid={`lab-${lab.id}`} className="block rounded-xl focus-visible:outline-offset-4">
                <Card className="h-full transition-colors hover:border-emerald-700">
                  <div className="flex flex-wrap items-center gap-2"><ModeBadge mode={lab.mode} /><DifficultyBadge difficulty={lab.difficulty} />
                    {lab.completed && <span className="ml-auto text-sm text-emerald-300">✓ пройдено</span>}</div>
                  <h3 className="mt-3 font-semibold">{lab.title}</h3>
                  <p className="mt-1 line-clamp-3 text-sm text-slate-400">{lab.description}</p>
                  <p className="mt-3 text-xs text-slate-500">~{lab.estimated_minutes} мин · {lab.base_xp} XP</p>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
