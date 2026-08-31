from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from auditra.ai_provider import GeminiInvestigationProvider, HuggingFaceInvestigationProvider, OfflineStructuredProvider, OpenRouterInvestigationProvider, TransparentFallbackInvestigationProvider, runtime_investigation_provider
from auditra.financial_world.understanding import GeminiWorldSpecProvider, OpenRouterWorldSpecProvider, WorldUnderstandingService
from auditra.llm import (
    GEMINI_API_URL_TEMPLATE,
    HUGGINGFACE_API_URL,
    OPENROUTER_API_URL,
    GeminiProvider,
    HuggingFaceProvider,
    LLMProviderConfig,
    LLMUnavailable,
    OpenRouterProvider,
    REAL_GEMINI_AI,
    REAL_HUGGINGFACE_AI,
    REAL_OPENROUTER_AI,
    resolve_llm_provider,
    AI_UNAVAILABLE,
)
from auditra.runtime import runtime_ai_status


class MultiProviderTests(unittest.TestCase):
    def test_gemini_native_request_and_observability(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["key"] = request.headers["x-goog-api-key"]
            captured["body"] = json.loads(request.content)
            return gemini_response({"candidate_labels": ["matched_low_risk"]})

        config = LLMProviderConfig.from_gemini_env()
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-test"}, clear=False):
            response = GeminiProvider(config=config, transport=httpx.MockTransport(handler)).generate_structured(
                "Plan", {"type": "object"}, "Return JSON.", {"case_id": "CASE_1"}
            )

        self.assertEqual(captured["url"], GEMINI_API_URL_TEMPLATE.format(model=config.model))
        self.assertEqual(captured["key"], "gemini-test")
        self.assertEqual(captured["body"]["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(response.provider, "gemini")
        self.assertEqual(response.model, config.model)
        self.assertEqual(response.total_tokens, 18)

    def test_openrouter_chat_request_shape(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers["Authorization"]
            captured["body"] = json.loads(request.content)
            return chat_response({"candidate_labels": ["matched_low_risk"]}, model="test/openrouter:free")

        config = LLMProviderConfig(provider="openrouter", model="test/openrouter:free", max_tokens=321, timeout_seconds=3)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-test"}, clear=False):
            response = OpenRouterProvider(config=config, transport=httpx.MockTransport(handler)).generate_structured(
                "Plan", {"type": "object"}, "Return JSON.", {}
            )

        self.assertEqual(captured["url"], OPENROUTER_API_URL)
        self.assertEqual(captured["authorization"], "Bearer or-test")
        self.assertEqual(captured["body"]["max_tokens"], 321)
        self.assertEqual(response.provider, "openrouter")

    def test_huggingface_chat_request_shape(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["authorization"] = request.headers["Authorization"]
            return chat_response({"candidate_labels": ["matched_low_risk"]}, model="openai/gpt-oss-120b:fastest")

        config = LLMProviderConfig(provider="huggingface", model="openai/gpt-oss-120b:fastest", timeout_seconds=3)
        with patch.dict(os.environ, {"HF_TOKEN": "hf-test"}, clear=False):
            response = HuggingFaceProvider(config=config, transport=httpx.MockTransport(handler)).generate_structured(
                "Plan", {"type": "object"}, "Return JSON.", {}
            )

        self.assertEqual(captured["url"], HUGGINGFACE_API_URL)
        self.assertEqual(captured["authorization"], "Bearer hf-test")
        self.assertEqual(response.provider, "huggingface")

    def test_provider_budget_limits_real_calls_per_run(self) -> None:
        class SuccessfulProvider:
            provider_name = "fast"
            model_name = "fast-model"
            prompt_version = "test"
            execution_mode = REAL_GEMINI_AI

            def __init__(self) -> None:
                self.calls = 0

            def propose(self, context):
                self.calls += 1
                return {
                    "candidate_labels": ["matched_low_risk"],
                    "tool_plan": [],
                    "self_challenge": [],
                    "verification_requirements": [],
                    "confidence_factors": {},
                    "provider": self.provider_name,
                    "model": self.model_name,
                    "execution_mode": self.execution_mode,
                    "prompt_version": self.prompt_version,
                    "usage": None,
                    "provider_trace": [],
                }

        primary = SuccessfulProvider()
        with patch.dict(os.environ, {"AUDITRA_EXTERNAL_LLM_CASE_LIMIT": "2"}, clear=False):
            provider = TransparentFallbackInvestigationProvider(primary, OfflineStructuredProvider())
        first = provider.propose({})
        second = provider.propose({})
        third = provider.propose({"status": "AMOUNT_MISMATCH", "reason_codes": []})

        self.assertEqual(primary.calls, 2)
        self.assertEqual(first["execution_mode"], REAL_GEMINI_AI)
        self.assertEqual(second["execution_mode"], REAL_GEMINI_AI)
        self.assertEqual(third["execution_mode"], "OFFLINE_AI")
        self.assertEqual(third["fallback_reason"], "provider_budget_exhausted")

    def test_runtime_selection_prefers_explicit_provider_and_hides_keys(self) -> None:
        with patch.dict(os.environ, {"AUDITRA_LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "never-show"}, clear=False):
            payload = runtime_ai_status()
            self.assertEqual(resolve_llm_provider("INVESTIGATION"), "gemini")
        self.assertEqual(payload["investigation"]["execution_mode"], REAL_GEMINI_AI)
        self.assertNotIn("never-show", json.dumps(payload))


    def test_ai_provider_alias_and_groq_first_auto_selection(self) -> None:
        with patch.dict(os.environ, {"AI_PROVIDER": "groq", "GROQ_API_KEY": "g-test"}, clear=False):
            self.assertEqual(resolve_llm_provider("INVESTIGATION"), "groq")
            payload = runtime_ai_status()
        self.assertEqual(payload["investigation"]["execution_mode"], "REAL_GROQ_AI")
        self.assertNotIn("g-test", json.dumps(payload))

        with patch.dict(os.environ, {"GROQ_API_KEY": "g-test", "GEMINI_API_KEY": "gemini-test", "HF_TOKEN": "hf-test"}, clear=True):
            self.assertEqual(resolve_llm_provider("WORLD"), "groq")

    def test_unsupported_provider_is_honest_and_falls_back(self) -> None:
        with patch.dict(os.environ, {"AI_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "anthropic-test"}, clear=True):
            payload = runtime_ai_status()
            provider = runtime_investigation_provider()
            proposal = provider.propose({"status": "AMOUNT_MISMATCH", "reason_codes": []})
        self.assertEqual(payload["investigation"]["provider"], "anthropic")
        self.assertEqual(payload["investigation"]["execution_mode"], AI_UNAVAILABLE)
        self.assertEqual(payload["investigation"]["implementation"], "architecture_supported_not_integrated")
        self.assertEqual(proposal["execution_mode"], "OFFLINE_AI")
        self.assertEqual(proposal["fallback_reason"], "provider_not_integrated")

    def test_adapter_labels_for_new_providers(self) -> None:
        plan = {
            "candidate_labels": ["refund_adjustment"],
            "tool_plan": [{"hypothesis_label": "refund_adjustment", "tool_name": "find_refunds", "arguments": {}, "reason": "Inspect refunds"}],
            "self_challenge": ["Could fees contradict this?"],
            "verification_requirements": ["Deterministic verification must pass."],
            "confidence_factors": {"provider_confidence": 0.8},
        }
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-test", "OPENROUTER_API_KEY": "or-test", "HF_TOKEN": "hf-test"}, clear=False):
            gemini = GeminiInvestigationProvider(GeminiProvider(transport=httpx.MockTransport(lambda _: gemini_response(plan)))).propose({})
            openrouter = OpenRouterInvestigationProvider(OpenRouterProvider(transport=httpx.MockTransport(lambda _: chat_response(plan, "or-model")))).propose({})
            huggingface = HuggingFaceInvestigationProvider(HuggingFaceProvider(transport=httpx.MockTransport(lambda _: chat_response(plan, "hf-model")))).propose({})
        self.assertEqual(gemini["execution_mode"], REAL_GEMINI_AI)
        self.assertEqual(openrouter["execution_mode"], REAL_OPENROUTER_AI)
        self.assertEqual(huggingface["execution_mode"], REAL_HUGGINGFACE_AI)

    def test_provider_failure_opens_circuit_for_the_rest_of_the_run(self) -> None:
        class SlowBrokenProvider:
            provider_name = "broken"
            model_name = "broken-model"
            prompt_version = "test"
            execution_mode = REAL_HUGGINGFACE_AI

            def __init__(self) -> None:
                self.calls = 0

            def propose(self, context):
                self.calls += 1
                raise LLMUnavailable("provider timed out", failure_type="timeout", attempts=1, latency_ms=1000)

        primary = SlowBrokenProvider()
        provider = TransparentFallbackInvestigationProvider(primary, OfflineStructuredProvider())
        first = provider.propose({"status": "AMOUNT_MISMATCH", "reason_codes": []})
        second = provider.propose({"status": "MISSING_SETTLEMENT", "reason_codes": []})

        self.assertEqual(primary.calls, 1)
        self.assertEqual(first["fallback_reason"], "timeout")
        self.assertEqual(second["fallback_reason"], "provider_circuit_open:timeout")
        self.assertEqual(second["execution_mode"], "OFFLINE_AI")


    def test_world_understanding_service_routes_implemented_providers(self) -> None:
        spec = {
            "world_name": "Provider Commerce",
            "merchant_name": "Provider Commerce",
            "record_count": 75,
            "currencies": ["INR"],
            "payment_methods": ["UPI", "CARD"],
            "fee_rate": "0.0200",
            "settlement_delay_days": 2,
            "anomaly_rates": {"REFUND_MISMATCH": "0.0200"},
        }
        with patch.dict(os.environ, {"AI_PROVIDER": "gemini", "GEMINI_API_KEY": "gemini-test"}, clear=True):
            result, steps = WorldUnderstandingService(
                gemini=GeminiWorldSpecProvider(GeminiProvider(transport=httpx.MockTransport(lambda _: gemini_response(spec))))
            ).understand("Build", 90)
        self.assertEqual(result.seed, 90)
        self.assertEqual(steps[0].metadata["provider"], "gemini")
        self.assertEqual(steps[0].metadata["execution_mode"], REAL_GEMINI_AI)

    def test_world_adapters_validate_new_provider_specs(self) -> None:
        spec = {
            "world_name": "Provider Commerce",
            "merchant_name": "Provider Commerce",
            "record_count": 75,
            "currencies": ["INR"],
            "payment_methods": ["UPI", "CARD"],
            "fee_rate": "0.0200",
            "settlement_delay_days": 2,
            "anomaly_rates": {"REFUND_MISMATCH": "0.0200"},
        }
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-test", "OPENROUTER_API_KEY": "or-test"}, clear=False):
            gemini_spec, gemini_steps = GeminiWorldSpecProvider(GeminiProvider(transport=httpx.MockTransport(lambda _: gemini_response(spec)))).parse("Build", 88)
            router_spec, router_steps = OpenRouterWorldSpecProvider(OpenRouterProvider(transport=httpx.MockTransport(lambda _: chat_response(spec, "or-model")))).parse("Build", 89)
        self.assertEqual(gemini_spec.seed, 88)
        self.assertEqual(router_spec.seed, 89)
        self.assertEqual(gemini_steps[0].metadata["execution_mode"], REAL_GEMINI_AI)
        self.assertEqual(router_steps[0].metadata["execution_mode"], REAL_OPENROUTER_AI)


def chat_response(output: dict, model: str) -> httpx.Response:
    return httpx.Response(200, json={
        "id": "chatcmpl-test",
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": json.dumps(output)}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14},
    })


def gemini_response(output: dict) -> httpx.Response:
    return httpx.Response(200, json={
        "responseId": "gemini-test-response",
        "candidates": [{"content": {"parts": [{"text": json.dumps(output)}]}}],
        "usageMetadata": {"promptTokenCount": 12, "candidatesTokenCount": 6, "totalTokenCount": 18},
    })


if __name__ == "__main__":
    unittest.main()





