import type {
  AuditWorldResult,
  AssuranceReport,
  ChallengeDefinition,
  ControllerComparison,
  FinancialWorldSpec,
  HealthResponse,
  ReviewAction,
  RedTeamResult,
  ScenarioMode,
  WorldBuildResult,
  WorldPreview,
} from "../types/auditra";

const API_BASE = import.meta.env.VITE_AUDITRA_API_BASE ?? "http://127.0.0.1:8002";

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

async function blobRequest(path: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }
  return response.blob();
}

export const auditraApi = {
  health: () => request<HealthResponse>("/health"),
  challenges: () =>
    request<{ challenges: ChallengeDefinition[]; default_challenge_id: string }>("/challenges"),
  buildChallenge: (challengeId: string, recordCount: number, seed: number) =>
    request<WorldBuildResult>(`/challenges/${encodeURIComponent(challengeId)}/build`, {
      method: "POST",
      body: JSON.stringify({ record_count: recordCount, seed }),
    }),
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
  ingest: (adapter: "json" | "csv" | "razorpay_test", payload: Record<string, unknown>, seed = 42) =>
    request<import("../types/auditra").IngestionResult>(`/ingest/${encodeURIComponent(adapter)}`, {
      method: "POST",
      body: JSON.stringify({ payload, seed }),
    }),
  auditWorld: (worldId: string) =>
    request<AuditWorldResult>(`/worlds/${encodeURIComponent(worldId)}/audit`, {
      method: "POST",
    }),
  assurance: (evaluationRunId: string) =>
    request<AssuranceReport>(`/audits/${encodeURIComponent(evaluationRunId)}/assurance`),
  submissionReport: (evaluationRunId: string) =>
    request<Record<string, unknown>>(`/reports/${encodeURIComponent(evaluationRunId)}`),
  exceptionReportCsv: (evaluationRunId: string) =>
    blobRequest(`/reports/${encodeURIComponent(evaluationRunId)}/exceptions.csv`),
  settlementBrief: (evaluationRunId: string) =>
    request<import("../types/auditra").SettlementBrief>(`/reports/${encodeURIComponent(evaluationRunId)}/settlement-brief`),
  redTeam: (evaluationRunId: string, recordCount = 200, seed = 84) =>
    request<RedTeamResult>(`/audits/${encodeURIComponent(evaluationRunId)}/red-team`, {
      method: "POST",
      body: JSON.stringify({ record_count: recordCount, seed }),
    }),
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
