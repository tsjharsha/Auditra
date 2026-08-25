import type { PageId, PrimaryPageId } from "../types/auditra";

export function normalizePageId(page: PageId): PrimaryPageId {
  if (page === "world-builder" || page === "world-explorer" || page === "worlds") return "worlds";
  if (page === "reconciliation" || page === "audits") return "audits";
  if (page === "investigations" || page === "evidence-graph" || page === "human-review" || page === "review") return "review";
  if (page === "evaluation-lab" || page === "controller-runs" || page === "audit-trail" || page === "insights") return "insights";
  if (page === "settings") return "settings";
  return "home";
}
