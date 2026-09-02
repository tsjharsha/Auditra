from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import auditra  # noqa: F401  # loads project .env without printing secrets
from auditra.assurance import assurance_report
from auditra.evaluator import IndependentEvaluator
from auditra.financial_world import FinancialWorldService
from auditra.models import ControllerRun, DatasetBundle, EvaluationRun
from auditra.reconciliation import ReconciliationEngine
from auditra.runtime import controller_execution_metadata, runtime_ai_status

DEFAULT_ARTIFACT_PATH = ROOT / "artifacts" / "real_groq_smoke.json"
ARTIFACT_PATH = DEFAULT_ARTIFACT_PATH
PROMPT = (
    "Build an Indian e-commerce merchant with 80 orders, UPI and card payments, "
    "2% platform fees, 18% GST on platform fees, T+2 settlement, refunds, stressed anomaly coverage with refund mismatches, partial settlements, "
    "duplicates, timing issues and conflicting evidence."
)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _write_artifact(payload: Dict[str, Any]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _set_provider(provider: str) -> None:
    os.environ["AI_PROVIDER"] = provider
    os.environ["AUDITRA_LLM_PROVIDER"] = provider
    os.environ["AUDITRA_WORLD_LLM_PROVIDER"] = provider
    os.environ["AUDITRA_INVESTIGATION_LLM_PROVIDER"] = provider


def _clear_provider() -> None:
    for key in ("AI_PROVIDER", "AUDITRA_LLM_PROVIDER", "AUDITRA_WORLD_LLM_PROVIDER", "AUDITRA_INVESTIGATION_LLM_PROVIDER"):
        os.environ.pop(key, None)


def _summarize(dataset: DatasetBundle, run: ControllerRun, evaluation: EvaluationRun) -> Dict[str, Any]:
    metrics = evaluation.metrics
    execution = controller_execution_metadata(run)
    traces = [trace for case in run.cases if case.ai_investigation for trace in case.ai_investigation.provider_trace]
    fallback_reasons = Counter(
        case.ai_investigation.fallback_reason
        for case in run.cases
        if case.ai_investigation and case.ai_investigation.fallback_reason
    )
    failure_types = Counter(
        str(trace.get("failure_type"))
        for trace in traces
        if trace.get("success") is False and trace.get("failure_type")
    )
    token_totals = _sum_trace_tokens(traces)
    confusion_totals = _confusion_totals(metrics.confusion_matrix)
    financial_review = _financial_review_amounts(dataset, run)
    return {
        "dataset_id": evaluation.dataset_id,
        "controller_run_id": run.run_id,
        "evaluation_run_id": evaluation.evaluation_run_id,
        "provider": execution["provider"],
        "model": execution["model"],
        "mode": execution["execution_mode"],
        "mode_counts": execution["mode_counts"],
        "record_count": run.metrics.transactions_processed,
        "exception_count": sum(1 for case in run.cases if str(case.status) not in {"MATCHED", "FEE_EXPLAINED", "REFUND_ADJUSTED"}),
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "true_positives": confusion_totals["true_positives"],
        "true_negatives": confusion_totals["true_negatives"],
        "false_positives": confusion_totals["false_positives"],
        "false_negatives": confusion_totals["false_negatives"],
        "false_positive_rate": metrics.false_positive_rate,
        "false_negative_rate": metrics.false_negative_rate,
        "exception_false_positive_rate": metrics.exception_false_positive_rate,
        "exception_false_negative_rate": metrics.exception_false_negative_rate,
        "failures": len(evaluation.failures),
        "auto_resolution_rate": metrics.automatic_resolution_rate,
        "human_escalation_rate": metrics.escalation_rate,
        "unresolved_rate": metrics.unresolved_rate,
        "financial_volume": str(run.metrics.total_payment_volume),
        "financial_amount_correctly_reconciled": str(metrics.financial_amount_correctly_reconciled),
        "financial_amount_incorrectly_classified": str(metrics.financial_amount_incorrectly_classified),
        "financial_amount_escalated": financial_review["escalated"],
        "financial_amount_unresolved": financial_review["unresolved"],
        "financial_error_impact": str(metrics.financial_impact_of_errors),
        "p50_latency_ms": metrics.median_latency_ms,
        "p95_latency_ms": metrics.p95_latency_ms,
        "throughput_records_per_sec": metrics.throughput_records_per_sec,
        "llm_calls": metrics.llm_calls,
        "ai_invocation_rate": run.metrics.ai_invocation_rate,
        "input_tokens": token_totals["input_tokens"],
        "output_tokens": token_totals["output_tokens"],
        "total_tokens": token_totals["total_tokens"],
        "estimated_cost_usd": str(metrics.estimated_ai_cost_usd) if metrics.estimated_ai_cost_usd is not None else None,
        "provider_failures": execution["provider_failures"],
        "fallback_count": execution["fallback_count"],
        "real_provider_calls": execution["real_provider_calls"],
        "successful_real_calls": sum(1 for trace in traces if trace.get("success") and trace.get("execution_mode") == "REAL_GROQ_AI"),
        "fallback_reasons": dict(sorted(fallback_reasons.items())),
        "failure_types": dict(sorted(failure_types.items())),
        "confusion_matrix": metrics.confusion_matrix,
        "class_metrics": metrics.class_metrics,
        "failure_taxonomy": metrics.failure_taxonomy,
    }



def _confusion_totals(matrix: Dict[str, Dict[str, int]]) -> Dict[str, int]:
    labels = sorted(set(matrix) | {predicted for row in matrix.values() for predicted in row})
    total = sum(int(count) for row in matrix.values() for count in row.values())
    true_positives = sum(int(matrix.get(label, {}).get(label, 0)) for label in labels)
    false_positives = sum(
        int(matrix.get(actual, {}).get(label, 0))
        for label in labels
        for actual in labels
        if actual != label
    )
    false_negatives = sum(
        int(matrix.get(label, {}).get(predicted, 0))
        for label in labels
        for predicted in labels
        if predicted != label
    )
    true_negatives = max(0, (len(labels) * total) - true_positives - false_positives - false_negatives)
    return {
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def _financial_review_amounts(dataset: DatasetBundle, run: ControllerRun) -> Dict[str, str]:
    payment_amounts = {payment.payment_id: payment.amount for payment in dataset.payments}
    escalated = Decimal("0.00")
    unresolved = Decimal("0.00")
    for case in run.cases:
        amount = payment_amounts.get(case.payment_id, case.decision.financial_impact)
        if str(case.status) == "HUMAN_REVIEW":
            escalated += amount
        if str(case.status) == "UNRESOLVED":
            unresolved += amount
    return {"escalated": str(escalated), "unresolved": str(unresolved)}


def _smoke_cases(run: ControllerRun, limit: int = 10) -> list[Dict[str, Any]]:
    rows = []
    for case in run.cases:
        ai = case.ai_investigation
        if ai is None:
            continue
        trace = ai.provider_trace[0] if ai.provider_trace else {}
        rows.append({
            "case_id": case.case_id,
            "payment_id": case.payment_id,
            "provider": ai.provider,
            "model": ai.model,
            "mode": ai.mode,
            "success": not ai.ai_unavailable and ai.fallback_reason is None,
            "fallback_reason": ai.fallback_reason,
            "decision": str(case.status),
            "verification_passed": case.decision.verification.passed if case.decision.verification else None,
            "latency_ms": ai.provider_latency_ms,
            "input_tokens": ai.input_tokens,
            "output_tokens": ai.output_tokens,
            "total_tokens": ai.total_tokens,
            "estimated_cost_usd": str(ai.estimated_cost_usd) if ai.estimated_cost_usd is not None else None,
            "trace_success": trace.get("success"),
            "trace_failure_type": trace.get("failure_type"),
        })
        if len(rows) >= limit:
            break
    return rows

def _sum_trace_tokens(traces: Iterable[Dict[str, Any]]) -> Dict[str, Optional[int]]:
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    known = {key: True for key in totals}
    for trace in traces:
        if not trace.get("success"):
            continue
        for key in totals:
            value = trace.get(key)
            if value is None:
                known[key] = False
            else:
                totals[key] += int(value)
    return {key: totals[key] if known[key] else None for key in totals}


def _lift(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "accuracy_delta": round(right["accuracy"] - left["accuracy"], 4),
        "f1_delta": round(right["f1"] - left["f1"], 4),
        "financial_error_delta": str(Decimal(str(right["financial_error_impact"])) - Decimal(str(left["financial_error_impact"]))),
        "auto_resolution_delta": round(right["auto_resolution_rate"] - left["auto_resolution_rate"], 4),
        "human_review_delta": round(right["human_escalation_rate"] - left["human_escalation_rate"], 4),
    }


def _run_controller(dataset: DatasetBundle, *, label: str, provider: Optional[str], enable_ai: bool) -> Dict[str, Any]:
    if provider:
        _set_provider(provider)
    else:
        _clear_provider()
    run = ReconciliationEngine(enable_ai=enable_ai).run(dataset)
    evaluation = IndependentEvaluator().evaluate(dataset, run)
    return {"label": label, "run": run, "evaluation": evaluation, "summary": _summarize(dataset, run, evaluation)}


def _blocked(reason: str) -> Dict[str, Any]:
    return {
        "artifact": "real_groq_smoke",
        "status": "BLOCKED_MISSING_KEY",
        "reason": reason,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": runtime_ai_status(),
        "secret_safety": {
            "secrets_printed": False,
            "secrets_written": False,
            "frontend_receives_api_key": False,
        },
    }


def main() -> int:
    global ARTIFACT_PATH
    parser = argparse.ArgumentParser(description="Run a bounded, honest Groq validation smoke test.")
    parser.add_argument("--records", type=int, default=20, choices=range(10, 51), metavar="N", help="Synthetic records to process (10-50).")
    parser.add_argument("--output", type=Path, default=DEFAULT_ARTIFACT_PATH, help="Artifact path; defaults to artifacts/real_groq_smoke.json.")
    args = parser.parse_args()
    ARTIFACT_PATH = args.output if args.output.is_absolute() else ROOT / args.output
    if not os.getenv("GROQ_API_KEY"):
        payload = _blocked("GROQ_API_KEY is not configured in the process or project .env")
        _write_artifact(payload)
        print(json.dumps({"status": payload["status"], "reason": payload["reason"], "artifact": str(ARTIFACT_PATH)}))
        return 2

    os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-20b")
    os.environ.setdefault("AUDITRA_EXTERNAL_LLM_CASE_LIMIT", "10")
    os.environ.setdefault("AUDITRA_EXTERNAL_LLM_TIMEOUT_CAP", "12")
    os.environ.setdefault("AUDITRA_EXTERNAL_LLM_MAX_RETRIES_CAP", "0")

    _set_provider("groq")
    service = FinancialWorldService()
    smoke_prompt = PROMPT.replace("80 orders", f"{args.records} orders")
    world = service.build_from_prompt(smoke_prompt, seed=202)
    if world.dataset is None:
        raise RuntimeError("world builder did not produce a dataset")

    deterministic = _run_controller(world.dataset, label="DETERMINISTIC", provider=None, enable_ai=False)
    offline = _run_controller(world.dataset, label="OFFLINE_AI", provider="offline", enable_ai=True)
    groq = _run_controller(world.dataset, label="REAL_GROQ_AI", provider="groq", enable_ai=True)
    groq_assurance = assurance_report(world.dataset, groq["run"], groq["evaluation"])

    groq_modes = groq["summary"]["mode_counts"]
    provider_truth = {
        "world_builder_provider": world.understanding_steps[0].metadata.get("provider") if world.understanding_steps else "unknown",
        "world_builder_mode": world.understanding_steps[0].metadata.get("execution_mode") if world.understanding_steps else "unknown",
        "investigation_mode_counts": groq_modes,
        "actual_llm_calls": groq["summary"]["llm_calls"],
        "real_provider_calls": controller_execution_metadata(groq["run"])["real_provider_calls"],
        "world_builder_llm_calls": int(world.understanding_steps[0].metadata.get("llm_calls") or 0) if world.understanding_steps else 0,
        "total_real_llm_calls": (int(world.understanding_steps[0].metadata.get("llm_calls") or 0) if world.understanding_steps else 0) + controller_execution_metadata(groq["run"])["real_provider_calls"],
    }

    rate_limited = any(
        "rate_limit" in str(key).lower()
        for key in [*groq["summary"].get("fallback_reasons", {}), *groq["summary"].get("failure_types", {})]
    )
    full_real_path = (
        provider_truth["world_builder_provider"] == "groq"
        and provider_truth["world_builder_mode"] == "REAL_GROQ_AI"
        and provider_truth["actual_llm_calls"] > 0
        and provider_truth["real_provider_calls"] > 0
        and groq["summary"]["mode"] == "REAL_GROQ_AI"
    )
    if full_real_path and groq["summary"]["fallback_count"] == 0 and groq["summary"]["provider_failures"] == 0:
        status = "PASS_FULL_REAL"
    elif full_real_path and rate_limited:
        status = "PARTIAL_RATE_LIMITED"
    elif full_real_path and groq["summary"]["fallback_count"] > 0:
        status = "PASS_WITH_FALLBACK"
    else:
        status = "FAILED_PROVIDER"

    payload = {
        "artifact": "real_groq_smoke",
        "artifact_version": 2,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "prompt": smoke_prompt,
            "seed": 202,
            "world_id": world.world_id,
            "dataset_id": world.dataset_id,
            "dataset_version": world.world_version,
            "requested_records": args.records,
            "record_count": world.dataset.requested_records,
            "case_limit": int(os.getenv("AUDITRA_EXTERNAL_LLM_CASE_LIMIT", "10")),
        },
        "controller_version": "auditra-0.4.0",
        "runtime": runtime_ai_status(),
        "provider_truth": provider_truth,
        "provider_evidence": {
            "provider": groq["summary"]["provider"],
            "model": groq["summary"]["model"],
            "world_builder_llm_calls": int(world.understanding_steps[0].metadata.get("llm_calls") or 0) if world.understanding_steps else 0,
        "total_real_llm_calls": (int(world.understanding_steps[0].metadata.get("llm_calls") or 0) if world.understanding_steps else 0) + controller_execution_metadata(groq["run"])["real_provider_calls"],
            "investigation_real_llm_calls": groq["summary"]["real_provider_calls"],
            "total_real_llm_calls": (int(world.understanding_steps[0].metadata.get("llm_calls") or 0) if world.understanding_steps else 0) + groq["summary"]["real_provider_calls"],
            "world_builder_successful_real_calls": 1 if world.understanding_steps and world.understanding_steps[0].metadata.get("success") and world.understanding_steps[0].metadata.get("execution_mode") == "REAL_GROQ_AI" else 0,
            "investigation_successful_real_calls": groq["summary"]["successful_real_calls"],
            "successful_real_calls": (1 if world.understanding_steps and world.understanding_steps[0].metadata.get("success") and world.understanding_steps[0].metadata.get("execution_mode") == "REAL_GROQ_AI" else 0) + groq["summary"]["successful_real_calls"],
            "fallback_calls": groq["summary"]["fallback_count"],
            "fallback_reasons": groq["summary"]["fallback_reasons"],
            "provider_failures": groq["summary"]["provider_failures"],
        },
        "world_builder": {
            "provider": provider_truth["world_builder_provider"],
            "mode": provider_truth["world_builder_mode"],
            "model": world.understanding_steps[0].metadata.get("model") if world.understanding_steps else None,
            "steps": [step.model_dump(mode="json") for step in world.understanding_steps],
        },
        "runs": {
            "deterministic": deterministic["summary"],
            "offline_ai": offline["summary"],
            "real_groq_ai": groq["summary"],
        },
        "smoke_cases": _smoke_cases(groq["run"], limit=10),
        "ai_lift": {
            "real_groq_vs_deterministic": _lift(deterministic["summary"], groq["summary"]),
            "real_groq_vs_offline_ai": _lift(offline["summary"], groq["summary"]),
        },
        "assurance": groq_assurance,
        "provenance": {
            "artifact_source": str(ARTIFACT_PATH.relative_to(ROOT)),
            "dataset_id": world.dataset_id,
            "controller_version": "auditra-0.4.0",
            "provider": "groq",
            "model": groq["summary"]["model"],
            "mode": groq["summary"]["mode"],
            "record_count": groq["summary"]["record_count"],
        },
        "limitations": [
            "Groq is used only for prompt interpretation and investigation planning.",
            "Financial records, verification, evaluation, and assurance remain deterministic.",
            "Token or cost fields are null when the provider does not return enough information.",
        ],
        "secret_safety": {
            "secrets_printed": False,
            "secrets_written": False,
            "frontend_receives_api_key": False,
        },
    }
    _write_artifact(payload)
    print(json.dumps({"status": status, "artifact": str(ARTIFACT_PATH), "llm_calls": groq["summary"]["llm_calls"]}, indent=2))
    return 0 if status in {"PASS_FULL_REAL", "PASS_WITH_FALLBACK", "PARTIAL_RATE_LIMITED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
