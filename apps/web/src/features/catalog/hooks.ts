import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/client";
import type { CourseModules, LabCard, LabList, Progress, SessionHistory } from "../../types/api";

export interface LabFilters {
  mode?: string;
  difficulty?: string;
  completed?: string; // "true" | "false" | ""
  availability?: string; // "available" | "unavailable" | ""
}

export function useLabs(filters: LabFilters) {
  const params = new URLSearchParams({ limit: "100" });
  for (const [k, v] of Object.entries(filters)) if (v) params.set(k, v);
  return useQuery({ queryKey: ["labs", filters], queryFn: () => api<LabList>(`/labs?${params}`) });
}

export function useModules() {
  return useQuery({ queryKey: ["modules"], queryFn: () => api<CourseModules>("/courses/linux-upskill/modules") });
}

export function useLab(labId: string) {
  return useQuery({ queryKey: ["lab", labId], queryFn: () => api<LabCard>(`/labs/${labId}`) });
}

export function useProgress() {
  return useQuery({ queryKey: ["progress"], queryFn: () => api<Progress>("/users/me/progress") });
}

export function useSessionHistory(limit = 20) {
  return useQuery({
    queryKey: ["sessions", limit],
    queryFn: () => api<SessionHistory>(`/users/me/sessions?limit=${limit}`),
  });
}
