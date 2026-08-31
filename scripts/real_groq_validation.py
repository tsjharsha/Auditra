from __future__ import annotations

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

ARTIFACT_PATH = ROOT / "artifacts" / "real_groq.json"
PROMPT = (
    "Build an Indian e-commerce merchant with 80 orders, UPI and card payments, "
    "2% platform fees, T+2 settlement, refunds, refund mismatches, partial settlements, "
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


def _summarize(run: ControllerRun, evaluation: EvaluationRun) -> Dict[str, Any]:
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
    return {
        "dataset_id": evaluation.dataset_id,
        "controller_run_id": run.run_id,
        "evaluation_run_id": evaluation.evaluation_run_id,
        "provider": execution["provider"],
        "model": execution["model"],
        "mode": execution["execution_mode"],
        "mode_counts": execution["mode_counts"],
        "record_count": run.metrics.transactions_processed,
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "false_positive_rate": metrics.false_positive_rate,
        "false_negative_rate": metrics.false_negative_rate,
        "failures": len(evaluation.failures),
        "auto_resolution_rate": metrics.automatic_resolution_rate,
        "human_escalation_rate": metrics.escalation_rate,
        "unresolved_rate": metrics.unresolved_rate,
        "financial_volume": str(run.metrics.total_payment_volume),
        "financial_amount_correctly_reconciled": str(metrics.financial_amount_correctly_reconciled),
        "financial_amount_incorrectly_classified": str(metrics.financial_amount_incorrectly_classified),
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
        "fallback_reasons": dict(sorted(fallback_reasons.items())),
        "failure_types": dict(sorted(failure_types.items())),
        "class_metrics": metrics.class_metrics,
        "failure_taxonomy": metrics.failure_taxonomy,
    }


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
    return {"label": label, "run": run, "evaluation": evaluation, "summary": _summarize(run, evaluation)}


def _blocked(reason: str) -> Dict[str, Any]:
    return {
        "artifact": "real_groq",
        "status": "BLOCKED",
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
    world = service.build_from_prompt(PROMPT, seed=202)
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
    }

    status = "PASS" if (
        provider_truth["world_builder_provider"] == "groq"
        and provider_truth["world_builder_mode"] == "REAL_GROQ_AI"
        and provider_truth["actual_llm_calls"] > 0
        and groq["summary"]["mode"] == "REAL_GROQ_AI"
    ) else "PARTIAL"

    payload = {
        "artifact": "real_groq",
        "artifact_version": 1,
        "status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "prompt": PROMPT,
            "seed": 202,
            "world_id": world.world_id,
            "dataset_id": world.dataset_id,
            "dataset_version": world.world_version,
            "record_count": world.dataset.requested_records,
        },
        "controller_version": "auditra-0.4.0",
        "runtime": runtime_ai_status(),
        "provider_truth": provider_truth,
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
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
