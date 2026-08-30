import type { PageId, PrimaryPageId } from "../types/auditra";

export function normalizePageId(page: PageId): PrimaryPageId {
  if (page === "world-builder" || page === "world-explorer") return "worlds";
  if (page === "reconciliation") return "audits";
  if (page === "investigations" || page === "evidence-graph" || page === "human-review") return "review";
  if (page === "evaluation-lab" || page === "controller-runs" || page === "audit-trail") return "insights";
  return page as PrimaryPageId;
}
