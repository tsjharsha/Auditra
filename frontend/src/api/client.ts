import type {
  AuditWorldResult,
  ControllerComparison,
  FinancialWorldSpec,
  ReviewAction,
  ScenarioMode,
  WorldBuildResult,
  WorldPreview,
} from "../types/auditra";

const API_BASE = import.meta.env.VITE_AUDITRA_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const auditraApi = {
  health: () => request<{ status: string; product: string }>("/health"),
  previewWorld: (prompt: string, seed: number) =>
    request<WorldPreview>("/worlds/preview", {
      method: "POST",
      body: JSON.stringify({ prompt, seed }),
    }),
  buildWorld: (prompt: string, seed: number) =>
    request<WorldBuildResult>("/worlds/build", {
      method: "POST",
      body: JSON.stringify({ prompt, seed }),
    }),
  buildWorldFromSpec: (spec: FinancialWorldSpec) =>
    request<WorldBuildResult>("/worlds/spec", {
      method: "POST",
      body: JSON.stringify(spec),
    }),
  auditWorld: (worldId: string) => request<AuditWorldResult>(`/worlds/${encodeURIComponent(worldId)}/audit`, { method: "POST" }),
  compare: (body: { dataset_id?: string; mode?: ScenarioMode; record_count?: number; seed?: number }) =>
    request<ControllerComparison>("/evaluation/compare", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  demo: (body: { mode: ScenarioMode; record_count: number; seed: number }) =>
    request<{
      dataset: unknown;
      controller_run: { run_id: string; metrics: unknown };
      evaluation: unknown;
      survival_status: string;
    }>("/demo", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  review: (caseId: string, runId: string, action: ReviewAction, reviewer: string, note: string) =>
    request<{ case_id: string; action: ReviewAction; reviewer: string; note: string; recorded: boolean }>(
      `/review/${encodeURIComponent(caseId)}?run_id=${encodeURIComponent(runId)}`,
      {
        method: "POST",
        body: JSON.stringify({ action, reviewer, note }),
      },
    ),
};

export { API_BASE };
