import type { PageId, PrimaryPageId } from "../types/auditra";

export function normalizePageId(page: PageId): PrimaryPageId {
  if (page === "home" || page === "world-builder" || page === "world-explorer" || page === "worlds") return "home";
  return "audits";
}
