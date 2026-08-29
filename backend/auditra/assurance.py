from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any, Dict, Iterable, List

from .financial_world import FinancialWorldSpec
from .models import ControllerRun, DatasetBundle, EvaluationRun
from .reconciliation import MATCH_STATUSES, TERMINAL_REVIEW_STATUSES


ASSURANCE_MODEL_VERSION = "auditra-assurance-v1"
MATCH_VALUES = {item.value for item in MATCH_STATUSES}
REVIEW_VALUES = {item.value for item in TERMINAL_REVIEW_STATUSES}

CHALLENGES: List[Dict[str, Any]] = [
    {
        "challenge_id": "settlement-reconciliation", "name": "Settlement & Reconciliation",
        "description": "Close a Razorpay-style payment batch across orders, fees, refunds, and T+2 settlements.",
        "risk": "Incorrect settlement closure can hide merchant exposure and reconciliation breaks.",
        "recommended": True, "record_count": 500, "anomaly_mode": "STRESSED", "accent": "cyan",
    },
    {
        "challenge_id": "refund-integrity", "name": "Refund Integrity Attack",
        "description": "Test post-settlement refunds, partial refunds, and conflicting refund evidence.",
        "risk": "Refunds can be detached from the original payment and silently distort net settlement.",
        "recommended": False, "record_count": 400, "anomaly_mode": "ADVERSARIAL", "accent": "rose",
    },
    {
        "challenge_id": "fee-leakage", "name": "Fee Leakage Control",
        "description": "Verify pricing rules and detect fee drift across payment methods.",
        "risk": "Small fee errors compound into material merchant and platform leakage.",
        "recommended": False, "record_count": 400, "anomaly_mode": "STRESSED", "accent": "amber",
    },
    {
        "challenge_id": "black-swan-close", "name": "Black Swan Close",
        "description": "Compound duplicates, delays, missing links, and contradictory evidence.",
        "risk": "Interacting anomalies can make a confident controller unsafe under peak pressure.",
        "recommended": False, "record_count": 600, "anomaly_mode": "CHAOS", "accent": "indigo",
    },
]


def challenge_by_id(challenge_id: str) -> Dict[str, Any]:
    for challenge in CHALLENGES:
        if challenge["challenge_id"] == challenge_id:
            return challenge
    raise KeyError(f"challenge not found: {challenge_id}")


def challenge_spec(challenge_id: str, record_count: int | None = None, seed: int = 42) -> FinancialWorldSpec:
    challenge = challenge_by_id(challenge_id)
    rates = {
        "settlement-reconciliation": {
            "AMOUNT_MISMATCH": "0.0350", "MISSING_SETTLEMENT": "0.0300", "FEE_MISMATCH": "0.0200",
            "REFUND_MISMATCH": "0.0250", "PARTIAL_SETTLEMENT": "0.0300", "TIMING_MISMATCH": "0.0250",
        },
        "refund-integrity": {
            "REFUND_MISMATCH": "0.1000", "PARTIAL_SETTLEMENT": "0.0500", "TIMING_MISMATCH": "0.0400",
            "CONFLICTING_EVIDENCE": "0.0600", "ENTITY_LINK_FAILURE": "0.0300",
        },
        "fee-leakage": {
            "FEE_MISMATCH": "0.1100", "AMOUNT_MISMATCH": "0.0450",
            "PARTIAL_SETTLEMENT": "0.0300", "CURRENCY_MISMATCH": "0.0200",
        },
        "black-swan-close": {
            "AMOUNT_MISMATCH": "0.0750", "MISSING_SETTLEMENT": "0.0650", "DUPLICATE_PAYMENT": "0.0500",
            "FEE_MISMATCH": "0.0500", "REFUND_MISMATCH": "0.0550", "PARTIAL_SETTLEMENT": "0.0550",
            "TIMING_MISMATCH": "0.0550", "CONFLICTING_EVIDENCE": "0.0600", "ENTITY_LINK_FAILURE": "0.0350",
        },
    }
    return FinancialWorldSpec(
        prompt=f"{challenge['name']} challenge with hidden ground truth and controlled finance anomalies.",
        world_name=f"Auditra {challenge['name']} Lab", merchant_name="NovaCart India", country="IN",
        record_count=record_count or int(challenge["record_count"]), seed=seed, currencies=["INR"],
        payment_methods=["UPI", "CARD", "WALLET"], fee_rate="0.0200", settlement_delay_days=2,
        refund_rate="0.0800", partial_settlement_rate="0.0300", anomaly_mode=challenge["anomaly_mode"],
        anomaly_rates=rates[challenge_id],
        constraints=["hidden_ground_truth", "immutable_seed", "enterprise_close_controls"],
        source="auditra_challenge_catalog", understanding_source="challenge_preset",
    )


def assurance_report(dataset: DatasetBundle, run: ControllerRun, evaluation: EvaluationRun) -> Dict[str, Any]:
    truth = dataset.ground_truth
    cases = [case for case in run.cases if case.payment_id in truth]
    auto_cases = [case for case in cases if str(case.status) in MATCH_VALUES]
    safe_auto = sum(1 for case in auto_cases if str(case.status) == str(truth[case.payment_id].expected_status))
    unsafe = [case for case in auto_cases if str(truth[case.payment_id].expected_status) not in MATCH_VALUES]
    escalated = [case for case in cases if str(case.status) in REVIEW_VALUES]
    correct_escalations = sum(1 for case in escalated if str(truth[case.payment_id].expected_status) not in MATCH_VALUES)
    evidence_complete = sum(1 for case in cases if case.evidence and case.invariants and case.decision.verification is not None)
    total_volume = max(Decimal(str(run.metrics.total_payment_volume)), Decimal("0.01"))
    error_impact = Decimal(str(evaluation.metrics.financial_impact_of_errors))
    dimensions = {
        "accuracy": evaluation.metrics.accuracy,
        "safe_autonomy": safe_auto / max(len(auto_cases), 1),
        "correct_escalation": correct_escalations / max(len(escalated), 1),
        "anomaly_detection": 1.0 - evaluation.metrics.false_negative_rate,
        "financial_impact_control": max(0.0, 1.0 - float(error_impact / total_volume)),
        "evidence_coverage": evidence_complete / max(len(cases), 1),
    }
    weights = {
        "accuracy": 0.35, "safe_autonomy": 0.20, "correct_escalation": 0.15,
        "anomaly_detection": 0.15, "financial_impact_control": 0.10, "evidence_coverage": 0.05,
    }
    raw_score = sum(dimensions[key] * weight for key, weight in weights.items()) * 100
    unsafe_exposure = sum((truth[case.payment_id].financial_impact for case in unsafe), Decimal("0.00"))
    unsafe_penalty = min(35.0, len(unsafe) * 6.0 + float(unsafe_exposure / total_volume) * 100)
    score = round(max(0.0, raw_score - unsafe_penalty), 1)
    recommendation = _recommendation(score, len(unsafe))
    return {
        "report_id": f"ASR_{evaluation.evaluation_run_id.removeprefix('EVAL_')}",
        "model_version": ASSURANCE_MODEL_VERSION, "dataset_id": dataset.dataset_id,
        "controller_run_id": run.run_id, "evaluation_run_id": evaluation.evaluation_run_id,
        "score": score, "grade": _grade(score), "recommendation": recommendation,
        "recommendation_detail": _recommendation_detail(recommendation),
        "dimensions": {key: round(value, 4) for key, value in dimensions.items()}, "weights": weights,
        "unsafe_auto_actions": len(unsafe), "unsafe_auto_action_penalty": round(unsafe_penalty, 1),
        "unsafe_exposure": str(unsafe_exposure.quantize(Decimal("0.01"))),
        "measured_error_impact": str(error_impact.quantize(Decimal("0.01"))),
        "failure_fingerprint": failure_fingerprint(evaluation.failures),
        "controls": [
            {"control": "Ground truth isolation", "status": "PASSED", "detail": "Truth was withheld until independent evaluation."},
            {"control": "Evidence traceability", "status": "PASSED" if dimensions["evidence_coverage"] == 1 else "REVIEW", "detail": f"{evidence_complete}/{len(cases)} decisions carry evidence, invariants, and verification."},
            {"control": "Unsafe autonomy", "status": "PASSED" if not unsafe else "FAILED", "detail": f"{len(unsafe)} exception cases were auto-closed as normal."},
            {"control": "Reproducibility", "status": "PASSED", "detail": f"Dataset is reproducible from seed {dataset.seed}."},
        ],
    }


def failure_fingerprint(failures: Iterable[Any]) -> Dict[str, Any]:
    items = list(failures)
    if not items:
        return {
            "pattern": "NO_MEASURED_FAILURE", "expected_status": None, "frequency": 0, "severity": "LOW",
            "exposure": "0.00", "root_cause": "No controller decisions differed from hidden ground truth.",
            "target_anomalies": ["CONFLICTING_EVIDENCE", "REFUND_MISMATCH", "TIMING_MISMATCH"],
        }
    pattern, frequency = Counter(item.failure_category for item in items).most_common(1)[0]
    candidates = [item for item in items if item.failure_category == pattern]
    expected = Counter(str(item.expected) for item in candidates).most_common(1)[0][0]
    exposure = sum((Decimal(str(item.financial_impact)) for item in candidates), Decimal("0.00"))
    return {
        "pattern": pattern, "expected_status": expected, "frequency": frequency,
        "severity": "CRITICAL" if exposure >= Decimal("10000") or pattern == "MISSED_EXCEPTION" else "HIGH",
        "exposure": str(exposure.quantize(Decimal("0.01"))), "root_cause": candidates[0].root_cause,
        "target_anomalies": _target_anomalies(pattern, expected),
    }


def targeted_retest_spec(dataset: DatasetBundle, evaluation: EvaluationRun, record_count: int, seed: int) -> FinancialWorldSpec:
    fingerprint = failure_fingerprint(evaluation.failures)
    targets = fingerprint["target_anomalies"]
    rates = {name: "0.1200" if index == 0 else "0.0750" for index, name in enumerate(targets[:4])}
    return FinancialWorldSpec(
        prompt=f"Targeted adversarial retest for {fingerprint['pattern']} using {', '.join(targets)}.",
        world_name="Auditra Targeted Red Team", merchant_name="NovaCart India Red Team", country="IN",
        record_count=record_count, seed=seed, currencies=["INR"], payment_methods=["UPI", "CARD", "WALLET"],
        fee_rate="0.0200", settlement_delay_days=2, refund_rate="0.1000", partial_settlement_rate="0.0500",
        anomaly_mode="ADVERSARIAL", anomaly_rates=rates,
        constraints=["targeted_failure_replay", "hidden_ground_truth", f"source_dataset:{dataset.dataset_id}"],
        source="auditra_failure_fingerprint", understanding_source="targeted_variation_generator",
    )


def _target_anomalies(pattern: str, expected: str) -> List[str]:
    by_status = {
        "REFUND_ADJUSTED": ["REFUND_MISMATCH", "PARTIAL_SETTLEMENT", "CONFLICTING_EVIDENCE"],
        "FEE_EXPLAINED": ["FEE_MISMATCH", "AMOUNT_MISMATCH", "CURRENCY_MISMATCH"],
        "TIMING_MISMATCH": ["TIMING_MISMATCH", "MISSING_SETTLEMENT", "PARTIAL_SETTLEMENT"],
        "MISSING_SETTLEMENT": ["MISSING_SETTLEMENT", "ENTITY_LINK_FAILURE", "TIMING_MISMATCH"],
        "DUPLICATE": ["DUPLICATE_PAYMENT", "ENTITY_LINK_FAILURE", "CONFLICTING_EVIDENCE"],
    }
    if expected in by_status:
        return by_status[expected]
    if pattern == "MISSED_CONFLICT":
        return ["CONFLICTING_EVIDENCE", "ENTITY_LINK_FAILURE", "REFUND_MISMATCH"]
    return ["AMOUNT_MISMATCH", "REFUND_MISMATCH", "TIMING_MISMATCH"]


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def _recommendation(score: float, unsafe_actions: int) -> str:
    if score >= 90 and unsafe_actions == 0:
        return "CONTROLLED_DEPLOYMENT"
    if score >= 75 and unsafe_actions == 0:
        return "HUMAN_SUPERVISED"
    return "REMEDIATION_REQUIRED"


def _recommendation_detail(recommendation: str) -> str:
    return {
        "CONTROLLED_DEPLOYMENT": "Eligible for a limited deployment with monitoring, rollback, and exception review controls.",
        "HUMAN_SUPERVISED": "Use with human approval for exceptions until targeted controls improve assurance.",
        "REMEDIATION_REQUIRED": "Do not grant autonomous close authority until unsafe decisions are remediated and retested.",
    }[recommendation]
