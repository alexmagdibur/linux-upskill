import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { AcceptedSession, SessionView, ValidationResult } from "../../types/api";

const TRANSIENT = new Set(["CREATED", "PROVISIONING", "VALIDATING", "STOPPING"]);

export function useSession(sessionId: string) {
  return useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => api<SessionView>(`/sessions/${sessionId}`),
    refetchInterval: (q) => (q.state.data && TRANSIENT.has(q.state.data.status) ? 800 : 5000),
  });
}

export function useStartLab() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (labId: string) =>
      api<AcceptedSession>(`/labs/${labId}/sessions`, {
        method: "POST",
        headers: { "Idempotency-Key": crypto.randomUUID() },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

export function useStopSession(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<{ status: string }>(`/sessions/${sessionId}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["session", sessionId] });
      void qc.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}

export function useResetSession(sessionId: string) {
  return useMutation({
    mutationFn: () => api<AcceptedSession>(`/sessions/${sessionId}/reset`, { method: "POST" }),
  });
}

export function useNextHint(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api<SessionView>(`/sessions/${sessionId}/hints/next`, { method: "POST" }),
    onSuccess: (data) => qc.setQueryData(["session", sessionId], data),
  });
}

/** Запускает проверку и опрашивает результат, пока он не станет FINISHED/ERROR. */
export function useValidate(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<ValidationResult> => {
      const started = await api<{ attempt_id: string }>(`/sessions/${sessionId}/validate`, { method: "POST" });
      void qc.invalidateQueries({ queryKey: ["session", sessionId] });
      for (let i = 0; i < 80; i++) {
        const r = await api<ValidationResult>(`/sessions/${sessionId}/validations/${started.attempt_id}`);
        if (r.status !== "PENDING") return r;
        await new Promise((res) => setTimeout(res, 600));
      }
      throw new Error("timeout");
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["session", sessionId] });
      void qc.invalidateQueries({ queryKey: ["me"] });
      void qc.invalidateQueries({ queryKey: ["progress"] });
      void qc.invalidateQueries({ queryKey: ["labs"] });
    },
  });
}

export function useValidationResult(sessionId: string, attemptId: string) {
  return useQuery({
    queryKey: ["validation", attemptId],
    queryFn: () => api<ValidationResult>(`/sessions/${sessionId}/validations/${attemptId}`),
  });
}
