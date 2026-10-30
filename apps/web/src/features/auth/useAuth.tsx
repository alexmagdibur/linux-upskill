import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";

import { ApiError, api } from "../../api/client";
import type { User } from "../../types/api";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const me = useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<User>("/users/me");
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) return null;
        throw e;
      }
    },
    staleTime: 30_000,
  });

  const loginM = useMutation({
    mutationFn: (v: { email: string; password: string }) => api<User>("/auth/login", { method: "POST", body: v }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  });
  const registerM = useMutation({
    mutationFn: (v: { email: string; password: string; display_name?: string }) =>
      api<User>("/auth/register", { method: "POST", body: v }),
  });
  const logoutM = useMutation({
    mutationFn: () => api<void>("/auth/logout", { method: "POST" }),
    onSuccess: () => {
      qc.clear();
      qc.setQueryData(["me"], null);
    },
  });

  const value: AuthState = {
    user: me.data ?? null,
    loading: me.isLoading,
    login: async (email, password) => {
      await loginM.mutateAsync({ email, password });
    },
    register: async (email, password, displayName) => {
      await registerM.mutateAsync({ email, password, display_name: displayName || undefined });
      await loginM.mutateAsync({ email, password });
    },
    logout: async () => {
      await logoutM.mutateAsync();
    },
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth вне AuthProvider");
  return v;
}
