import type { ReconciliationStatus } from "../types/auditra";

export const healthyStatuses: ReconciliationStatus[] = ["MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"];
export const reviewStatuses: ReconciliationStatus[] = ["HUMAN_REVIEW", "UNRESOLVED"];

export function statusTone(status?: string) {
  if (!status) return "muted";
  if (healthyStatuses.includes(status as ReconciliationStatus)) return "success";
  if (reviewStatuses.includes(status as ReconciliationStatus)) return "review";
  if (["AMOUNT_MISMATCH", "MISSING_SETTLEMENT"].includes(status)) return "danger";
  return "warning";
}

export function riskTone(risk?: number) {
  if ((risk ?? 0) >= 60) return "danger";
  if ((risk ?? 0) >= 28) return "warning";
  if ((risk ?? 0) > 0) return "review";
  return "success";
}
