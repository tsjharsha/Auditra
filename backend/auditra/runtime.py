from __future__ import annotations

from collections import Counter
from typing import Any, Dict

from .llm import (
    AI_UNAVAILABLE,
    DETERMINISTIC,
    OFFLINE_AI,
    REAL_GEMINI_AI,
    REAL_HUGGINGFACE_AI,
    REAL_OPENROUTER_AI,
    REAL_GROQ_AI,
    REAL_OPENAI_AI,
    llm_runtime_status,
)
from .models import ControllerRun


def controller_execution_metadata(run: ControllerRun) -> Dict[str, Any]:
    investigations = [
        case.ai_investigation
        for case in run.cases
        if case.ai_investigation is not None
    ]
    if not investigations:
        return {
            "execution_mode": DETERMINISTIC,
            "provider": "deterministic",
            "model": "financial-control-engine",
            "prompt_version": None,
            "investigation_count": 0,
            "mode_counts": {DETERMINISTIC: len(run.cases)},
            "real_provider_calls": 0,
            "fallback_count": 0,
            "provider_failures": 0,
        }

    mode_counts = Counter(item.mode for item in investigations)
    ordered_modes = [REAL_GEMINI_AI, REAL_OPENROUTER_AI, REAL_GROQ_AI, REAL_HUGGINGFACE_AI, REAL_OPENAI_AI, OFFLINE_AI, AI_UNAVAILABLE]
    execution_mode = next((mode for mode in ordered_modes if mode_counts.get(mode)), investigations[0].mode)
    representative = next((item for item in investigations if item.mode == execution_mode), investigations[0])
    traces = [trace for item in investigations for trace in item.provider_trace]
    return {
        "execution_mode": execution_mode,
        "provider": representative.provider,
        "model": representative.model,
        "prompt_version": representative.prompt_version,
        "investigation_count": len(investigations),
        "mode_counts": dict(sorted(mode_counts.items())),
        "real_provider_calls": sum(
            int(trace.get("llm_calls") or 0)
            for trace in traces
            if trace.get("success") and trace.get("execution_mode") in {REAL_GEMINI_AI, REAL_OPENROUTER_AI, REAL_GROQ_AI, REAL_HUGGINGFACE_AI, REAL_OPENAI_AI}
        ),
        "fallback_count": sum(1 for item in investigations if item.fallback_reason),
        "provider_failures": sum(1 for trace in traces if trace.get("success") is False),
    }


def public_controller_run(run: ControllerRun) -> Dict[str, Any]:
    payload = run.model_dump(mode="json")
    payload["execution"] = controller_execution_metadata(run)
    return payload


def runtime_ai_status() -> Dict[str, Any]:
    return {
        "world_understanding": llm_runtime_status("WORLD"),
        "investigation": llm_runtime_status("INVESTIGATION"),
        "labels": {
            "deterministic": DETERMINISTIC,
            "offline": OFFLINE_AI,
            "groq": REAL_GROQ_AI,
            "gemini": REAL_GEMINI_AI,
            "openrouter": REAL_OPENROUTER_AI,
            "huggingface": REAL_HUGGINGFACE_AI,
        },
    }

