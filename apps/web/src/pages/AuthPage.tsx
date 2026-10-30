import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, friendlyMessage } from "../api/client";
import { Button, Card, ErrorBanner } from "../components/ui";
import { useAuth } from "../features/auth/useAuth";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isLogin) await login(email, password);
      else await register(email, password, name);
      nav("/dashboard");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const fieldErrors =
    error instanceof ApiError && error.code === "VALIDATION_ERROR"
      ? ((error.details.fields as { loc: string[]; msg: string }[] | undefined) ?? [])
      : [];

  return (
    <div className="mx-auto max-w-md py-8">
      <Card>
        <h1 className="text-2xl font-bold">{isLogin ? "Вход" : "Регистрация"}</h1>
        <form onSubmit={submit} className="mt-5 space-y-4" noValidate>
          {!isLogin && (
            <label className="block text-sm">
              <span className="text-slate-300">Имя (необязательно)</span>
              <input value={name} onChange={(e) => setName(e.target.value)} maxLength={100} autoComplete="name"
                className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2" />
            </label>
          )}
          <label className="block text-sm">
            <span className="text-slate-300">Email</span>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" name="email"
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span className="text-slate-300">Пароль {isLogin ? "" : "(минимум 8 символов)"}</span>
            <input type="password" required minLength={isLogin ? 1 : 8} value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete={isLogin ? "current-password" : "new-password"} name="password"
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2" />
          </label>
          {error != null && (
            <>
              <ErrorBanner error={error} />
              {fieldErrors.length > 0 && (
                <ul className="list-disc pl-5 text-sm text-rose-300">
                  {fieldErrors.map((f, i) => (<li key={i}>{f.loc.slice(-1)[0]}: {f.msg}</li>))}
                </ul>
              )}
            </>
          )}
          <Button type="submit" disabled={busy} className="w-full">{busy ? "Подождите…" : isLogin ? "Войти" : "Создать аккаунт"}</Button>
        </form>
        <p className="mt-4 text-sm text-slate-400">
          {isLogin ? (<>Нет аккаунта? <Link className="text-emerald-300 underline" to="/register">Зарегистрируйтесь</Link></>)
            : (<>Уже есть аккаунт? <Link className="text-emerald-300 underline" to="/login">Войдите</Link></>)}
        </p>
        <p className="sr-only" aria-live="polite">{error != null ? friendlyMessage(error) : ""}</p>
      </Card>
    </div>
  );
}
