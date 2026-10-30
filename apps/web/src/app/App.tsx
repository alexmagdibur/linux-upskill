import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";

import { ApiError } from "../api/client";
import { Layout } from "../components/Layout";
import { Spinner } from "../components/ui";
import { AuthProvider, useAuth } from "../features/auth/useAuth";
import { Catalog } from "../pages/Catalog";
import { Dashboard } from "../pages/Dashboard";
import { LabDetails } from "../pages/LabDetails";
import { Landing } from "../pages/Landing";
import { AuthPage } from "../pages/AuthPage";
import { Profile } from "../pages/Profile";
import { Result } from "../pages/Result";
import { Workspace } from "../pages/Workspace";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
    },
  },
});

function Protected() {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8"><Spinner /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function GuestOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8"><Spinner /></div>;
  return user ? <Navigate to="/dashboard" replace /> : <>{children}</>;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<GuestOnly><Landing /></GuestOnly>} />
              <Route path="login" element={<GuestOnly><AuthPage mode="login" /></GuestOnly>} />
              <Route path="register" element={<GuestOnly><AuthPage mode="register" /></GuestOnly>} />
              <Route element={<Protected />}>
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="catalog" element={<Catalog />} />
                <Route path="labs/:labId" element={<LabDetails />} />
                <Route path="workspace/:sessionId" element={<Workspace />} />
                <Route path="result/:sessionId/:attemptId" element={<Result />} />
                <Route path="profile" element={<Profile />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
