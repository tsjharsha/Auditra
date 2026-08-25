import type { AuditWorldResult, EvidenceItem, ReconciliationCase, ReconciliationStatus } from "../types/auditra";
import { healthyStatuses, reviewStatuses } from "./status";
import { titleCase } from "./format";

const caseTitles: Record<ReconciliationStatus, string> = {
  MATCHED: "Matched activity",
  PARTIAL_MATCH: "Partial match",
  FEE_EXPLAINED: "Fee explained",
  REFUND_ADJUSTED: "Refund adjusted",
  DUPLICATE: "Duplicate payment",
  MISSING_SETTLEMENT: "Settlement missing",
  AMOUNT_MISMATCH: "Settlement mismatch",
  TIMING_MISMATCH: "Timing mismatch",
  UNRESOLVED: "Needs investigation",
  HUMAN_REVIEW: "Needs review",
};

export function caseTitle(item: ReconciliationCase) {
  return caseTitles[item.status] ?? titleCase(item.status);
}

export function caseShortExplanation(item: ReconciliationCase) {
  if (item.status === "AMOUNT_MISMATCH") {
    return `Payment is ${item.decision.expected_settlement ?? "-"} while settlement is ${item.decision.actual_settlement ?? "-"}.`;
  }
  if (item.status === "MISSING_SETTLEMENT") {
    return "A payment was captured but a matching settlement could not be found.";
  }
  if (item.status === "TIMING_MISMATCH") {
    return "The transaction appears valid, but the settlement timing does not line up with the expected window.";
  }
  if (item.status === "DUPLICATE") {
    return "Multiple payment records appear to point to the same customer activity.";
  }
  if (item.status === "HUMAN_REVIEW" || item.status === "UNRESOLVED") {
    return item.decision.verification?.challenges[0] ?? "Auditra could not close this case with enough confidence.";
  }
  return item.ai_investigation?.rationale ?? item.decision.reason_codes[0] ?? "Auditra completed the check successfully.";
}

export function caseWhyItMatters(item: ReconciliationCase) {
  const selectedHypothesis = item.ai_investigation?.hypotheses.find(
    (hypothesis) => hypothesis.hypothesis_id === item.ai_investigation?.selected_hypothesis_id,
  );
  const fallbackReasons = item.decision.reason_codes.map(titleCase).join(", ");
  const explanation =
    selectedHypothesis?.rationale ??
    item.ai_investigation?.rationale ??
    item.decision.verification?.checks.find((check) => !check.passed)?.detail ??
    fallbackReasons;
  return explanation || "Auditra combined transaction evidence with verification checks to reach this outcome.";
}

export function caseEvidenceHighlights(item: ReconciliationCase, limit = 3) {
  const preferredIds = new Set([
    ...item.decision.supporting_evidence,
    ...item.decision.contradicting_evidence,
    ...(item.ai_investigation?.supporting_evidence_ids ?? []),
  ]);
  const highlighted = item.evidence.filter((entry) => preferredIds.has(entry.evidence_id));
  return (highlighted.length ? highlighted : item.evidence).slice(0, limit);
}

export function reviewPriority(item: ReconciliationCase) {
  if (healthyStatuses.includes(item.status)) return "Resolved";
  if (reviewStatuses.includes(item.status) || Number(item.decision.financial_impact) >= 1000 || item.risk_score >= 35) return "High priority";
  return "Medium priority";
}

export function sortCasesByAttention(cases: ReconciliationCase[]) {
  return [...cases].sort((a, b) => {
    const priorityScore = scorePriority(reviewPriority(b)) - scorePriority(reviewPriority(a));
    if (priorityScore !== 0) return priorityScore;
    return Number(b.decision.financial_impact) - Number(a.decision.financial_impact) || b.risk_score - a.risk_score;
  });
}

export function attentionCases(audit?: AuditWorldResult | null) {
  if (!audit) return [];
  return sortCasesByAttention(audit.controller_run.cases.filter((item) => !healthyStatuses.includes(item.status)));
}

export function resolvedCases(audit?: AuditWorldResult | null) {
  if (!audit) return [];
  return sortCasesByAttention(audit.controller_run.cases.filter((item) => healthyStatuses.includes(item.status)));
}

export function potentialExposure(cases: ReconciliationCase[]) {
  return cases.reduce((sum, item) => sum + Number(item.decision.financial_impact ?? 0), 0);
}

export function auditHealthRatio(audit?: AuditWorldResult | null) {
  if (!audit) return 0;
  const correct = Number(audit.evaluation.metrics.financial_amount_correctly_reconciled ?? 0);
  const total = Number(audit.controller_run.metrics.total_payment_volume ?? 0);
  if (total > 0 && Number.isFinite(correct)) return Math.min(1, Math.max(0, correct / total));
  return audit.evaluation.metrics.accuracy ?? 0;
}

export function auditHealthLabel(audit?: AuditWorldResult | null) {
  if (!audit) return "No audit yet";
  const reviewCount = attentionCases(audit).filter((item) => reviewStatuses.includes(item.status)).length;
  if (reviewCount > 0) return "Review required";
  if (attentionCases(audit).length > 0 || audit.evaluation.failures.length > 0) return "Attention needed";
  return "Healthy";
}

export function auditHealthTone(audit?: AuditWorldResult | null): "success" | "warning" | "review" {
  if (!audit) return "review";
  const label = auditHealthLabel(audit);
  if (label === "Healthy") return "success";
  if (label === "Review required") return "review";
  return "warning";
}

export function groupedReviewCases(audit?: AuditWorldResult | null) {
  const cases = audit?.controller_run.cases ?? [];
  return {
    high: sortCasesByAttention(cases.filter((item) => reviewPriority(item) === "High priority")),
    medium: sortCasesByAttention(cases.filter((item) => reviewPriority(item) === "Medium priority")),
    resolved: sortCasesByAttention(cases.filter((item) => reviewPriority(item) === "Resolved")),
  };
}

export function evidenceLabel(item: EvidenceItem) {
  return `${titleCase(item.entity_type)} evidence`;
}

function scorePriority(priority: string) {
  if (priority === "High priority") return 3;
  if (priority === "Medium priority") return 2;
  return 1;
}
