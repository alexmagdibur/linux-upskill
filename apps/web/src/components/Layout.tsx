import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../features/auth/useAuth";
import { Button } from "./ui";

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-slate-800 text-emerald-300" : "text-slate-300 hover:bg-slate-800"}`;

export function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-emerald-500 focus:px-3 focus:py-1 focus:text-slate-950">
        К содержимому
      </a>
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2 px-4 py-3">
          <NavLink to={user ? "/dashboard" : "/"} className="mr-4 flex items-center gap-2 text-lg font-bold">
            <span aria-hidden className="text-emerald-400">&gt;_</span> Linux Upskill
          </NavLink>
          {user && (
            <nav aria-label="Основная навигация" className="flex flex-wrap gap-1">
              <NavLink to="/dashboard" className={link}>Дашборд</NavLink>
              <NavLink to="/catalog" className={link}>Каталог</NavLink>
              <NavLink to="/profile" className={link}>Профиль</NavLink>
            </nav>
          )}
          <div className="ml-auto flex items-center gap-3">
            {user ? (
              <>
                <span data-testid="xp-total" className="rounded-full bg-emerald-900/50 px-3 py-1 text-sm text-emerald-200">
                  {user.total_xp ?? 0} XP
                </span>
                <span className="hidden text-sm text-slate-400 sm:inline">{user.display_name ?? user.email}</span>
                <Button variant="ghost" onClick={async () => { await logout(); nav("/"); }}>Выйти</Button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={link}>Войти</NavLink>
                <NavLink to="/register" className="rounded-md bg-emerald-500 px-3 py-1.5 text-sm font-semibold text-slate-950 hover:bg-emerald-400">Регистрация</NavLink>
              </>
            )}
          </div>
        </div>
      </header>
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
