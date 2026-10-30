import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Card, DifficultyBadge, EnvBadge, ErrorBanner, ModeBadge, PageTitle, Spinner } from "../components/ui";
import { useModules } from "../features/catalog/hooks";
import type { LabSummary } from "../types/api";

const select = "rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm";

interface Filters {
  mode: string;
  difficulty: string;
  completed: string;
  availability: string;
  q: string;
}

function matches(l: LabSummary, f: Filters): boolean {
  if (f.mode && l.mode !== f.mode) return false;
  if (f.difficulty && l.difficulty !== f.difficulty) return false;
  if (f.completed === "true" && !l.completed) return false;
  if (f.completed === "false" && l.completed) return false;
  if (f.availability === "available" && l.availability !== "available") return false;
  if (f.availability === "unavailable" && l.availability === "available") return false;
  const q = f.q.trim().toLowerCase();
  if (q && !`${l.title} ${l.description} ${l.topic ?? ""}`.toLowerCase().includes(q)) return false;
  return true;
}

export function Catalog() {
  const [f, setF] = useState<Filters>({ mode: "", difficulty: "", completed: "", availability: "available", q: "" });
  const modules = useModules();
  const set = (k: keyof Filters) => (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) =>
    setF((cur) => ({ ...cur, [k]: e.target.value }));

  const groups = useMemo(
    () =>
      (modules.data?.items ?? []).map((m) => ({
        ...m,
        shown: m.labs.filter((l) => matches(l, f)),
        runnable: m.labs.filter((l) => l.availability === "available").length,
      })),
    [modules.data, f],
  );
  const total = groups.reduce((n, g) => n + g.shown.length, 0);

  return (
    <div>
      <PageTitle sub="Четыре этапа: новичок → джун → мидл → синьор. Доступные задания запускаются в изолированной песочнице.">
        Каталог лабораторий
      </PageTitle>
      <form aria-label="Фильтры" className="mb-6 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
        <label className="text-sm text-slate-300">Поиск<br />
          <input className={select} value={f.q} onChange={set("q")} placeholder="название или тема" aria-label="Поиск" />
        </label>
        <label className="text-sm text-slate-300">Режим<br />
          <select className={select} value={f.mode} onChange={set("mode")} aria-label="Режим">
            <option value="">Все</option><option value="learn">Learn</option><option value="practice">Practice</option><option value="incident">Incident</option>
          </select>
        </label>
        <label className="text-sm text-slate-300">Сложность<br />
          <select className={select} value={f.difficulty} onChange={set("difficulty")} aria-label="Сложность">
            <option value="">Любая</option><option value="beginner">Начальный</option><option value="junior">Junior</option><option value="middle">Middle</option><option value="senior">Senior</option>
          </select>
        </label>
        <label className="text-sm text-slate-300">Статус<br />
          <select className={select} value={f.completed} onChange={set("completed")} aria-label="Статус">
            <option value="">Все</option><option value="false">Не пройдены</option><option value="true">Пройдены</option>
          </select>
        </label>
        <label className="text-sm text-slate-300">Доступность<br />
          <select className={select} value={f.availability} onChange={set("availability")} aria-label="Доступность">
            <option value="available">Можно запустить</option><option value="">Все задания</option><option value="unavailable">Требуют VM / несколько узлов</option>
          </select>
        </label>
        <span className="pb-2 text-sm text-slate-400" aria-live="polite">Найдено: {total}</span>
      </form>
      {modules.isLoading && <Spinner />}
      <ErrorBanner error={modules.error} />
      {modules.data && total === 0 && <p className="text-slate-400">По выбранным фильтрам ничего не найдено.</p>}
      {groups.filter((g) => g.shown.length > 0).map((g) => {
        let lastTopic = "";
        return (
          <section key={g.id} className="mb-10" aria-labelledby={`m-${g.id}`}>
            <h2 id={`m-${g.id}`} className="mb-1 text-xl font-semibold text-slate-100">{g.title}</h2>
            <p className="mb-4 text-sm text-slate-400">{g.description} · запускается {g.runnable} из {g.labs.length}</p>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {g.shown.flatMap((lab) => {
                const heading = lab.topic && lab.topic !== lastTopic ? lab.topic : null;
                if (lab.topic) lastTopic = lab.topic;
                const unavailable = lab.availability !== "available";
                return [
                  heading && (
                    <h3 key={`t-${lab.id}`} className="col-span-full mt-2 border-b border-slate-800 pb-1 text-sm font-semibold uppercase tracking-wide text-emerald-300">{heading}</h3>
                  ),
                  <Link key={lab.id} to={`/labs/${lab.id}`} data-testid={`lab-${lab.id}`} data-availability={lab.availability} className="block rounded-xl focus-visible:outline-offset-4">
                    <Card className={`h-full transition-colors hover:border-emerald-700 ${unavailable ? "opacity-70" : ""}`}>
                      <div className="flex flex-wrap items-center gap-2">
                        <ModeBadge mode={lab.mode} /><DifficultyBadge difficulty={lab.difficulty} /><EnvBadge environment={unavailable ? lab.environment : null} />
                        {lab.completed && <span className="ml-auto text-sm text-emerald-300">✓ пройдено</span>}
                      </div>
                      <h3 className="mt-3 font-semibold"><span className="mr-1 text-slate-500">{lab.lesson ? `#${lab.lesson}` : ""}</span>{lab.title}</h3>
                      <p className="mt-1 line-clamp-3 text-sm text-slate-400">{lab.description}</p>
                      <p className="mt-3 text-xs text-slate-500">~{lab.estimated_minutes} мин · {lab.base_xp} XP</p>
                    </Card>
                  </Link>,
                ];
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
