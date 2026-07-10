// Typed client for the RocmPilot backend.
// These types mirror backend/app/models.py — keep them in sync with the contract
// in docs/API_CONTRACT.md. If a request 4xx/5xxs, `request()` throws with the
// server's detail message so the UI can show it instead of failing silently.

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Severity = "low" | "medium" | "high" | "critical";
export type ActionType =
  | "auto_patch"
  | "suggested_patch"
  | "manual_review"
  | "info";
export type RunStage =
  | "created"
  | "scanned"
  | "planned"
  | "patched"
  | "validated"
  | "reported";

export interface ScoreBreakdown {
  before: number;
  after_planned: number | null;
  final: number | null;
}

export interface Finding {
  file_path: string;
  line_number: number;
  severity: Severity;
  category: string;
  matched_text: string;
  explanation: string;
  recommended_action: string;
  action_type: ActionType;
}

export interface PlanAction {
  title: string;
  detail: string;
  severity: Severity;
  action_type: ActionType;
}

export interface MigrationPlan {
  summary: string;
  actions: PlanAction[];
  manual_blockers: string[];
}

export interface Critique {
  approved: boolean;
  issues: string[];
  notes: string;
}

export interface AgentEvent {
  agent: string; // "orchestrator" | "planner" | "critic"
  message: string;
  ok: boolean;
}

export interface Artifact {
  name: string;
  path: string;
  language: string;
}

export interface ValidationResult {
  status: "passed" | "failed" | "not_run";
  mode: "live" | "replay";
  rocm_detected: boolean;
  hip_available: boolean;
  pytorch_rocm_build: string | null;
  gpu_name: string | null;
  smoke_test_passed: boolean;
  benchmark_passed: boolean;
  inference_latency_ms: number | null;
  logs: string;
}

export interface RunSummary {
  run_id: string;
  stage: RunStage;
  source: string;
  score: ScoreBreakdown;
}

export interface ScanResponse {
  run_id: string;
  findings: Finding[];
  findings_by_category: Record<string, number>;
  files_scanned: number;
  score: ScoreBreakdown;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  createRun: (body: { repo_url?: string; use_sample?: boolean }) =>
    request<RunSummary>("/api/runs", { method: "POST", body: JSON.stringify(body) }),
  scan: (id: string) =>
    request<ScanResponse>(`/api/runs/${id}/scan`, { method: "POST" }),
  plan: (id: string) =>
    request<{ run_id: string; plan: MigrationPlan; critique: Critique; trace: AgentEvent[] }>(
      `/api/runs/${id}/plan`,
      { method: "POST" },
    ),
  patch: (id: string) =>
    request<{ run_id: string; artifacts: Artifact[]; score: ScoreBreakdown }>(
      `/api/runs/${id}/patch`,
      { method: "POST" },
    ),
  validate: (id: string) =>
    request<{ run_id: string; validation: ValidationResult; score: ScoreBreakdown }>(
      `/api/runs/${id}/validate`,
      { method: "POST" },
    ),
  report: (id: string) =>
    request<{ run_id: string; markdown: string; score: ScoreBreakdown; artifacts: Artifact[] }>(
      `/api/runs/${id}/report`,
    ),
  artifact: (id: string, name: string) =>
    request<{ run_id: string; name: string; content: string }>(
      `/api/runs/${id}/artifacts/${name}`,
    ),
};
