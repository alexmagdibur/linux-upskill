export type Mode = "learn" | "practice" | "incident";
export type Difficulty = "beginner" | "junior" | "middle" | "senior";
export type Availability = "available" | "requires_vm" | "requires_cluster" | "requires_vm_container_runtime" | "manual_review";

export type SessionStatus =
  | "CREATED"
  | "PROVISIONING"
  | "READY"
  | "RUNNING"
  | "VALIDATING"
  | "COMPLETED"
  | "FAILED"
  | "STOPPING"
  | "STOPPED"
  | "EXPIRED";

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  created_at: string;
  total_xp?: number;
}

export interface LabSummary {
  id: string;
  uuid: string;
  title: string;
  description: string;
  mode: Mode;
  difficulty: Difficulty;
  estimated_minutes: number;
  module: { slug: string; title: string };
  base_xp: number;
  completed: boolean;
  best_score: number | null;
  attempts_count: number;
  lesson: number | null;
  topic: string | null;
  task_type: "L" | "P" | "I" | "C" | null;
  environment: "C" | "V" | "N" | "D" | null;
  availability: Availability;
  unavailable_reason: string | null;
}

export interface LabCard extends LabSummary {
  objectives: string[];
  skills: string[];
  hints_total: number;
  checks: string[];
  version: number;
  stage: string | null;
  theory: string | null;
  prediction: string | null;
  criterion: string | null;
  followups: Record<string, string>;
  task: string;
}

export interface LabList {
  items: LabSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface CourseModules {
  course: { id: string; title: string };
  items: { id: string; title: string; description: string; labs: LabSummary[] }[];
}

export interface AttemptBrief {
  attempt_id: string;
  status: "PENDING" | "FINISHED" | "ERROR";
  passed: boolean | null;
  score: number | null;
}

export interface SessionView {
  session_id: string;
  status: SessionStatus;
  expires_at: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_code: string | null;
  lab: { id: string; title: string; mode: Mode; difficulty: Difficulty; estimated_minutes: number; base_xp: number };
  task: string;
  theory: string | null;
  prediction: string | null;
  criterion: string | null;
  objectives: string[];
  checks: string[];
  hints_total: number;
  hints: string[];
  last_attempt: AttemptBrief | null;
}

export interface AcceptedSession {
  session_id: string;
  status: SessionStatus;
  expires_at: string;
  status_url: string;
}

export interface CheckResult {
  id: string;
  passed: boolean;
  message: string;
}

export interface ValidationResult {
  attempt_id: string;
  status: "PENDING" | "FINISHED" | "ERROR";
  passed: boolean | null;
  score: number | null;
  checks: CheckResult[];
  error_code: string | null;
  xp_awarded: number;
}

export interface Progress {
  total_xp: number;
  completed_labs: number;
  labs_total: number;
  items: { lab_id: string; title: string; best_score: number; attempts_count: number; completed_at: string | null }[];
  recent_attempts: {
    attempt_id: string;
    session_id: string;
    lab_id: string | null;
    passed: boolean | null;
    score: number | null;
    status: string;
    created_at: string;
  }[];
}

export interface SessionHistory {
  items: {
    session_id: string;
    lab_id: string;
    lab_title: string;
    status: SessionStatus;
    created_at: string;
    finished_at: string | null;
  }[];
  total: number;
  limit: number;
  offset: number;
}

export interface TerminalTicket {
  ticket: string;
  expires_in: number;
  ws_path: string;
}
