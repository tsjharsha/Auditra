from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import auditra  # noqa: F401  # loads project .env without printing secrets
from dotenv import load_dotenv
from auditra.ai_provider import (
    GeminiInvestigationProvider,
    GroqInvestigationProvider,
    HuggingFaceInvestigationProvider,
    OpenRouterInvestigationProvider,
    ProviderUsage,
    StructuredInvestigationProvider,
)
from auditra.evaluator import IndependentEvaluator
from auditra.financial_world import FinancialWorldService
from auditra.financial_world.understanding import DeterministicPromptParser
from auditra.llm import (
    AI_UNAVAILABLE,
    REAL_GEMINI_AI,
    REAL_GROQ_AI,
    REAL_HUGGINGFACE_AI,
    REAL_OPENROUTER_AI,
    LLMProviderConfig,
    LLMUnavailable,
    GeminiProvider,
)
from auditra.models import ControllerRun, DatasetBundle, EvaluationRun
from auditra.reconciliation import ReconciliationEngine

# Validation must exercise the credentials intentionally configured in this repository,
# not stale keys inherited from a developer's Windows environment.
load_dotenv(ROOT / ".env", override=True)

DEFAULT_ARTIFACT_PATH = ROOT / "artifacts" / "real_llm_validation.json"
PROVIDER_ORDER = ("groq", "gemini", "openrouter", "huggingface")
REAL_EXECUTION_MODES = {
    REAL_GROQ_AI,
    REAL_GEMINI_AI,
    REAL_OPENROUTER_AI,
    REAL_HUGGINGFACE_AI,
}
PROMPT = (
    "Build an Indian e-commerce merchant with {records} orders, UPI and card payments, "
    "2% platform fees, 18% GST on platform fees, T+2 settlement, refunds, and stressed "
    "anomaly coverage with refund mismatches, partial settlements, duplicates, timing issues, "
    "and conflicting evidence."
)


class RealProviderFailoverInvestigator(StructuredInvestigationProvider):
    """Validation-only failover across real providers; it never invokes offline planning."""

    provider_name = "real_provider_failover"
    model_name = "multiple_external_models"
    prompt_version = "investigation-plan-v2"

    def __init__(self, providers: Sequence[StructuredInvestigationProvider]):
        if not providers:
            raise ValueError("at least one real provider is required")
        self.providers = list(providers)
        self.case_attempts: Dict[str, List[Dict[str, Any]]] = {}

    def propose(self, context: Dict[str, Any]) -> Dict[str, Any]:
        case_key = str(context.get("payment_id") or "unknown_payment")
        attempts: List[Dict[str, Any]] = []
        for provider in self.providers:
            try:
                proposal = provider.propose(context)
            except Exception as exc:
                attempts.append(_failure_trace(provider, exc))
                continue

            success_trace = list(proposal.get("provider_trace") or [])
            combined_trace = [*attempts, *success_trace]
            usage = proposal.get("usage")
            proposal["usage"] = ProviderUsage(
                llm_calls=int(getattr(usage, "llm_calls", 0)),
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
                estimated_cost_usd=getattr(usage, "estimated_cost_usd", None),
                latency_ms=sum(float(trace.get("latency_ms") or 0.0) for trace in combined_trace),
                attempts=sum(int(trace.get("attempts") or 0) for trace in combined_trace),
            )
            proposal["provider_trace"] = combined_trace
            self.case_attempts[case_key] = combined_trace
            return proposal

        self.case_attempts[case_key] = attempts
        failure_types = sorted({str(trace.get("failure_type") or "provider_unavailable") for trace in attempts})
        primary_failure = "rate_limit" if "rate_limit" in failure_types else (failure_types[0] if failure_types else "provider_unavailable")
        raise LLMUnavailable(
            "all configured real providers failed: " + ", ".join(failure_types or ["provider_unavailable"]),
            failure_type=primary_failure,
            attempts=sum(int(trace.get("attempts") or 0) for trace in attempts),
            latency_ms=sum(float(trace.get("latency_ms") or 0.0) for trace in attempts),
        )


def _gemini_response_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten Pydantic JSON Schema into Gemini's supported response-schema subset."""
    definitions = copy.deepcopy(schema.get("$defs") or {})
    unsupported_keywords = {"$defs", "$schema", "additionalProperties", "default", "title"}

    def normalize(value: Any) -> Any:
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if not isinstance(value, dict):
            return value
        reference = value.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/$defs/"):
            definition_name = reference.removeprefix("#/$defs/")
            definition = definitions.get(definition_name)
            if isinstance(definition, dict):
                return normalize(definition)
        return {
            key: normalize(item)
            for key, item in value.items()
            if key not in unsupported_keywords and key != "$ref"
        }

    flattened = normalize(copy.deepcopy(schema))
    if not isinstance(flattened, dict):
        raise ValueError("Gemini response schema must be an object")
    return flattened


class ValidationGeminiProvider(GeminiProvider):
    """Validation-only Gemini adapter for Pydantic schemas that use local references."""

    def _request(
        self,
        api_key: str,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        try:
            return super()._request(api_key, schema_name, _gemini_response_schema(schema), system_prompt, user_payload)
        except LLMUnavailable as exc:
            if exc.failure_type != "invalid_request":
                raise
        fallback_prompt = (
            f"{system_prompt} Return only one JSON object matching this JSON Schema: "
            f"{json.dumps(schema, default=str)}"
        )
        return super()._request(api_key, schema_name, {"type": "object"}, fallback_prompt, user_payload)

def _failure_trace(provider: StructuredInvestigationProvider, exc: Exception) -> Dict[str, Any]:
    return {
        "execution_mode": getattr(provider, "execution_mode", AI_UNAVAILABLE),
        "provider": provider.provider_name,
        "model": provider.model_name,
        "prompt_version": provider.prompt_version,
        "timestamp": getattr(exc, "timestamp", None),
        "latency_ms": round(float(getattr(exc, "latency_ms", 0.0)), 4),
        "attempts": int(getattr(exc, "attempts", 0)),
        "llm_calls": 0,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "cost_usd": None,
        "success": False,
        "failure_type": str(getattr(exc, "failure_type", type(exc).__name__)),
    }


def _bounded(config: LLMProviderConfig, timeout_seconds: float) -> LLMProviderConfig:
    return replace(config, timeout_seconds=min(config.timeout_seconds, timeout_seconds), max_retries=0)


def provider_catalog(timeout_seconds: float) -> tuple[List[StructuredInvestigationProvider], List[Dict[str, Any]]]:
    entries = [
        ("groq", "GROQ_API_KEY", REAL_GROQ_AI, GroqInvestigationProvider, LLMProviderConfig.from_groq_env),
        ("gemini", "GEMINI_API_KEY", REAL_GEMINI_AI, GeminiInvestigationProvider, LLMProviderConfig.from_gemini_env),
        ("openrouter", "OPENROUTER_API_KEY", REAL_OPENROUTER_AI, OpenRouterInvestigationProvider, LLMProviderConfig.from_openrouter_env),
        ("huggingface", "HF_TOKEN/HF_API_KEY", REAL_HUGGINGFACE_AI, HuggingFaceInvestigationProvider, LLMProviderConfig.from_huggingface_env),
    ]
    providers: List[StructuredInvestigationProvider] = []
    catalog: List[Dict[str, Any]] = []
    for provider_name, credential_name, execution_mode, factory, config_factory in entries:
        config = _bounded(config_factory("AUDITRA_INVESTIGATION_LLM"), timeout_seconds)
        if provider_name == "huggingface":
            config = replace(config, max_tokens=max(config.max_tokens, 1600), max_retries=max(config.max_retries, 1))
        provider = (
            factory(llm_provider=ValidationGeminiProvider(config=config))
            if provider_name == "gemini"
            else factory(config=config)
        )
        configured = bool(os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")) if provider_name == "huggingface" else bool(os.getenv(credential_name))
        providers.append(provider)
        catalog.append(
            {
                "provider": provider_name,
                "model": config.model,
                "execution_mode": execution_mode,
                "configured": configured,
                "credential_env": credential_name,
                "timeout_seconds": config.timeout_seconds,
                "max_retries": config.max_retries,
            }
        )
    return providers, catalog


def _case_evidence(run: ControllerRun, failover: RealProviderFailoverInvestigator) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for case in run.cases:
        investigation = case.ai_investigation
        if investigation is None:
            continue
        attempts = failover.case_attempts.get(case.payment_id, [])
        successful_trace = next((trace for trace in attempts if trace.get("success") is True and trace.get("execution_mode") in REAL_EXECUTION_MODES), None)
        failures = [str(trace.get("failure_type")) for trace in attempts if trace.get("success") is False and trace.get("failure_type")]
        rows.append(
            {
                "case_id": case.case_id,
                "payment_id": case.payment_id,
                "result": "REAL_SUCCESS" if successful_trace else "FAILED_ALL_REAL_PROVIDERS",
                "provider_attempts": attempts,
                "successful_provider": successful_trace.get("provider") if successful_trace else None,
                "successful_model": successful_trace.get("model") if successful_trace else None,
                "failure_reasons": sorted(set(failures)),
                "controller_status": str(case.status),
                "verification_passed": case.decision.verification.passed if case.decision.verification else None,
                "ai_unavailable": investigation.ai_unavailable,
            }
        )
    return rows


def _validation_status(
    *, configured_provider_count: int, investigation_cases: int, successful_cases: int, failed_cases: int, offline_fallback_calls: int, rate_limit_events: int
) -> str:
    if configured_provider_count == 0:
        return "BLOCKED_MISSING_KEYS"
    if investigation_cases == 0:
        return "FAILED_NO_VALIDATION_CASES"
    if successful_cases == investigation_cases and failed_cases == 0 and offline_fallback_calls == 0:
        return "PASS_FULL_REAL"
    if successful_cases > 0 and rate_limit_events > 0:
        return "PARTIAL_RATE_LIMITED"
    if successful_cases > 0:
        return "PARTIAL_REAL"
    return "FAILED_PROVIDER"


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _write_artifact(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def _build_validation_world(records: int):
    prompt = PROMPT.format(records=records)
    spec, steps = DeterministicPromptParser().parse(prompt, seed=202)
    return FinancialWorldService().build_from_spec(spec, steps=steps), prompt


def run_validation(records: int, timeout_seconds: float) -> Dict[str, Any]:
    world, prompt = _build_validation_world(records)
    if world.dataset is None:
        raise RuntimeError("validation world did not produce a dataset")
    providers, catalog = provider_catalog(timeout_seconds)
    failover = RealProviderFailoverInvestigator(providers)
    run = ReconciliationEngine(enable_ai=True, ai_provider=failover).run(world.dataset)
    evaluation = IndependentEvaluator().evaluate(world.dataset, run)
    cases = _case_evidence(run, failover)
    traces = [trace for row in cases for trace in row["provider_attempts"]]
    successes = [row for row in cases if row["result"] == "REAL_SUCCESS"]
    failures = [row for row in cases if row["result"] != "REAL_SUCCESS"]
    provider_usage = Counter(str(row["successful_provider"]) for row in successes if row["successful_provider"])
    model_usage = Counter(str(row["successful_model"]) for row in successes if row["successful_model"])
    provider_failures = [trace for trace in traces if trace.get("success") is False]
    rate_limit_events = sum(1 for trace in provider_failures if trace.get("failure_type") == "rate_limit")
    offline_fallback_calls = sum(1 for trace in traces if trace.get("execution_mode") == "OFFLINE_AI")
    provider_failovers = sum(1 for row in successes if any(trace.get("success") is False for trace in row["provider_attempts"]))
    configured_provider_count = sum(1 for entry in catalog if entry["configured"])
    status = _validation_status(
        configured_provider_count=configured_provider_count,
        investigation_cases=len(cases),
        successful_cases=len(successes),
        failed_cases=len(failures),
        offline_fallback_calls=offline_fallback_calls,
        rate_limit_events=rate_limit_events,
    )
    return {
        "artifact": "real_llm_multi_provider_validation",
        "artifact_version": 1,
        "validation_status": status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_definition": {
            "controller_cases": "All reconciled payment cases in the deterministic validation world.",
            "investigation_cases": "Cases for which the existing controller requested an AI investigation.",
            "successful_cases": "Investigation cases completed by a real external provider.",
            "failed_cases": "Investigation cases where all four real providers failed; no offline plan was used.",
            "offline_fallback_calls": "Must remain zero for this validation mode.",
        },
        "dataset": {
            "prompt": prompt,
            "seed": 202,
            "world_id": world.world_id,
            "dataset_id": world.dataset_id,
            "dataset_version": world.world_version,
            "requested_records": records,
            "controller_cases": run.metrics.transactions_processed,
            "understanding_source": world.spec.understanding_source,
        },
        "provider_order": list(PROVIDER_ORDER),
        "providers": catalog,
        "total_cases": run.metrics.transactions_processed,
        "investigation_cases": len(cases),
        "successful_cases": len(successes),
        "failed_cases": len(failures),
        "not_required_cases": run.metrics.transactions_processed - len(cases),
        "real_llm_calls": sum(int(trace.get("llm_calls") or 0) for trace in traces if trace.get("success") is True and trace.get("execution_mode") in REAL_EXECUTION_MODES),
        "offline_fallback_calls": offline_fallback_calls,
        "provider_failures": len(provider_failures),
        "rate_limit_events": rate_limit_events,
        "provider_failovers": provider_failovers,
        "provider_usage": dict(sorted(provider_usage.items())),
        "model_usage": dict(sorted(model_usage.items())),
        "case_results": cases,
        "evaluation": {
            "evaluation_run_id": evaluation.evaluation_run_id,
            "accuracy": evaluation.metrics.accuracy,
            "precision": evaluation.metrics.precision,
            "recall": evaluation.metrics.recall,
            "f1": evaluation.metrics.f1,
            "financial_error_impact": str(evaluation.metrics.financial_impact_of_errors),
        },
        "normal_application_behavior": "Unchanged. This runner injects validation-only real-provider failover; normal runtime fallback remains intact.",
        "secret_safety": {
            "secrets_printed": False,
            "secrets_written": False,
            "frontend_receives_api_key": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a bounded real-provider-only Auditra validation.")
    parser.add_argument("--records", type=int, default=24, choices=range(20, 31), metavar="N", help="Synthetic source records to generate (20-30).")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-provider timeout cap in seconds.")
    parser.add_argument("--output", type=Path, default=DEFAULT_ARTIFACT_PATH, help="Artifact path; defaults to artifacts/real_llm_validation.json.")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    payload = run_validation(args.records, args.timeout)
    _write_artifact(output, payload)
    print(json.dumps({
        "validation_status": payload["validation_status"],
        "total_cases": payload["total_cases"],
        "investigation_cases": payload["investigation_cases"],
        "successful_cases": payload["successful_cases"],
        "failed_cases": payload["failed_cases"],
        "real_llm_calls": payload["real_llm_calls"],
        "offline_fallback_calls": payload["offline_fallback_calls"],
        "provider_failovers": payload["provider_failovers"],
        "artifact": str(output),
    }, indent=2))
    return 0 if payload["validation_status"] == "PASS_FULL_REAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())