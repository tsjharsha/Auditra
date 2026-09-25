from __future__ import annotations

from decimal import Decimal
from typing import List

from .models import CashPosition, ControllerAlert, ControllerRun, ReconciliationCase, ReconciliationStatus, money


CLOSED_STATUSES = {
    ReconciliationStatus.MATCHED.value,
    ReconciliationStatus.FEE_EXPLAINED.value,
    ReconciliationStatus.REFUND_ADJUSTED.value,
}

_ALERT_TITLES = {
    ReconciliationStatus.MISSING_SETTLEMENT.value: ("Settlement missing", "settlement"),
    ReconciliationStatus.AMOUNT_MISMATCH.value: ("Settlement variance", "settlement"),
    ReconciliationStatus.PARTIAL_MATCH.value: ("Partial settlement", "settlement"),
    ReconciliationStatus.TIMING_MISMATCH.value: ("Delayed settlement", "timing"),
    ReconciliationStatus.DUPLICATE.value: ("Duplicate payment", "payment"),
    ReconciliationStatus.HUMAN_REVIEW.value: ("Human review required", "review"),
    ReconciliationStatus.UNRESOLVED.value: ("Unresolved reconciliation", "review"),
}


def cash_position(run: ControllerRun) -> CashPosition:
    """Summarize authoritative settlement values already computed by reconciliation."""
    expected_cases = [case for case in run.cases if case.decision.expected_settlement is not None]
    settled_cases = [case for case in expected_cases if case.decision.actual_settlement is not None]
    unsettled_cases = [case for case in expected_cases if case.decision.actual_settlement is None]
    variance_cases = [
        case for case in settled_cases
        if abs(case.decision.difference or Decimal("0.00")) > Decimal("0.00")
    ]
    expected = money(sum((case.decision.expected_settlement or Decimal("0.00") for case in expected_cases), Decimal("0.00")))
    recorded = money(sum((case.decision.actual_settlement or Decimal("0.00") for case in settled_cases), Decimal("0.00")))
    pending = money(sum((case.decision.expected_settlement or Decimal("0.00") for case in unsettled_cases), Decimal("0.00")))
    variance = money(sum((abs(case.decision.difference or Decimal("0.00")) for case in variance_cases), Decimal("0.00")))
    status = "WITHIN_TOLERANCE"
    if variance_cases:
        status = "INVESTIGATION_REQUIRED"
    elif unsettled_cases:
        status = "PENDING_SETTLEMENT"
    return CashPosition(
        expected_net_settlement=expected,
        recorded_settlement=recorded,
        pending_unsettled=pending,
        settlement_variance=variance,
        expected_case_count=len(expected_cases),
        unsettled_case_count=len(unsettled_cases),
        variance_case_count=len(variance_cases),
        status=status,
    )


def controller_alerts(run: ControllerRun, limit: int = 4) -> List[ControllerAlert]:
    """Return the highest-priority current-run exceptions without consulting hidden truth."""
    open_cases = [case for case in run.cases if str(case.status) not in CLOSED_STATUSES]
    alerts = [_alert_from_case(case) for case in open_cases]
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "WARNING": 2, "RESOLVED": 3}
    alerts.sort(key=lambda alert: (severity_rank[alert.severity], -alert.financial_exposure, -alert.risk_score, alert.alert_id))
    if alerts:
        return alerts[:limit]

    explained = [case for case in run.cases if str(case.status) in {ReconciliationStatus.FEE_EXPLAINED.value, ReconciliationStatus.REFUND_ADJUSTED.value}]
    if not explained:
        return []
    return [
        ControllerAlert(
            alert_id=f"ALT_RESOLVED_{run.run_id}",
            severity="RESOLVED",
            category="reconciliation",
            title="Explained fee and refund adjustments",
            summary=f"{len(explained)} settlement adjustment(s) reconciled by deterministic controls.",
            status=ReconciliationStatus.MATCHED,
            financial_exposure=Decimal("0.00"),
            risk_score=0.0,
            verification_state="PASSED",
        )
    ]


def _alert_from_case(case: ReconciliationCase) -> ControllerAlert:
    status = str(case.status)
    title, category = _ALERT_TITLES.get(status, ("Reconciliation exception", "reconciliation"))
    reason_codes = set(case.decision.reason_codes)
    if any("REFUND" in code for code in reason_codes):
        title, category = "Refund reconciliation conflict", "refund"
    elif any("FEE" in code or "GST" in code for code in reason_codes):
        title, category = "Fee / GST variance", "fee_gst"
    exposure = money(case.decision.financial_impact)
    severity = _severity(case, exposure)
    verification = case.decision.verification
    verification_state = "NOT_APPLICABLE" if verification is None else ("PASSED" if verification.passed else "FAILED")
    summary = _summary(case)
    return ControllerAlert(
        alert_id=f"ALT_{case.case_id}",
        severity=severity,
        category=category,
        title=title,
        summary=summary,
        status=case.status,
        financial_exposure=exposure,
        risk_score=case.risk_score,
        case_id=case.case_id,
        payment_id=case.payment_id,
        verification_state=verification_state,
    )


def _severity(case: ReconciliationCase, exposure: Decimal) -> str:
    status = str(case.status)
    if status == ReconciliationStatus.MISSING_SETTLEMENT.value or exposure >= Decimal("10000.00") or case.risk_score >= 60:
        return "CRITICAL"
    if status in {
        ReconciliationStatus.HUMAN_REVIEW.value,
        ReconciliationStatus.UNRESOLVED.value,
        ReconciliationStatus.AMOUNT_MISMATCH.value,
        ReconciliationStatus.PARTIAL_MATCH.value,
        ReconciliationStatus.DUPLICATE.value,
    } or exposure > Decimal("0.00"):
        return "HIGH"
    return "WARNING"


def _summary(case: ReconciliationCase) -> str:
    verification = case.decision.verification
    if verification and verification.challenges:
        return verification.challenges[0]
    if case.decision.reason_codes:
        return case.decision.reason_codes[0].replace("_", " ").lower()
    if str(case.status) == ReconciliationStatus.TIMING_MISMATCH.value:
        return "Settlement timing is outside the configured close window."
    return "Evidence-backed reconciliation exception requires inspection."