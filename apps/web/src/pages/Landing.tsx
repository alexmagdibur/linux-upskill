import { Link } from "react-router-dom";

import { Card } from "../components/ui";

const STEPS = [
  { t: "Learn", d: "Короткая теория и направляющие подсказки: выполняйте конкретные действия в реальном терминале." },
  { t: "Practice", d: "Самостоятельно достигайте заданного состояния системы — мы проверяем результат, а не набранные команды." },
  { t: "Incident", d: "Диагностируйте и устраняйте искусственно созданные неисправности, как на реальном проде." },
];

export function Landing() {
  return (
    <div className="space-y-12 py-8">
      <section className="max-w-3xl">
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
          Учите Linux <span className="text-emerald-400">руками</span>, а не по скриншотам
        </h1>
        <p className="mt-5 text-lg text-slate-300">
          Linux Upskill запускает для вас изолированную Linux-песочницу прямо в браузере. Вы работаете в настоящем shell, а независимая
          проверка оценивает итоговое состояние системы и начисляет XP.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/register" className="rounded-md bg-emerald-500 px-5 py-2.5 font-semibold text-slate-950 hover:bg-emerald-400">Начать бесплатно</Link>
          <Link to="/login" className="rounded-md bg-slate-800 px-5 py-2.5 font-semibold hover:bg-slate-700">Войти</Link>
        </div>
      </section>
      <section aria-label="Обучающий путь" className="grid gap-4 md:grid-cols-3">
        {STEPS.map((s) => (
          <Card key={s.t}>
            <h2 className="text-lg font-semibold text-emerald-300">{s.t}</h2>
            <p className="mt-2 text-slate-300">{s.d}</p>
          </Card>
        ))}
      </section>
      <p className="text-sm text-slate-500">20 лабораторий в трёх модулях: Linux Basics, Administration, Incident Simulation.</p>
    </div>
  );
}
