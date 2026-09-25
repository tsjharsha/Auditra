from __future__ import annotations

import os
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from pydantic import ValidationError

from ..llm import (
    DETERMINISTIC,
    OFFLINE_AI,
    REAL_GEMINI_AI,
    REAL_HUGGINGFACE_AI,
    REAL_OPENROUTER_AI,
    REAL_GROQ_AI,
    REAL_OPENAI_AI,
    GeminiProvider as GeminiLLMProvider,
    GroqProvider as GroqLLMProvider,
    HuggingFaceProvider as HuggingFaceLLMProvider,
    OpenRouterProvider as OpenRouterLLMProvider,
    LLMInvalidResponse,
    LLMProvider,
    LLMProviderConfig,
    LLMUnavailable,
    OpenAIProvider as OpenAILLMProvider,
    resolve_llm_provider,
)
from .models import AnomalyMode, FinancialWorldSpec, UnderstandingStep, rate


DEFAULT_ANOMALIES = {
    AnomalyMode.NORMAL: {
        "AMOUNT_MISMATCH": Decimal("0.0100"),
        "MISSING_SETTLEMENT": Decimal("0.0100"),
        "TIMING_MISMATCH": Decimal("0.0100"),
    },
    AnomalyMode.STRESSED: {
        "AMOUNT_MISMATCH": Decimal("0.0500"),
        "MISSING_SETTLEMENT": Decimal("0.0300"),
        "DUPLICATE_PAYMENT": Decimal("0.0200"),
        "FEE_MISMATCH": Decimal("0.0300"),
        "REFUND_MISMATCH": Decimal("0.0200"),
        "PARTIAL_SETTLEMENT": Decimal("0.0300"),
        "TIMING_MISMATCH": Decimal("0.0300"),
        "CONFLICTING_EVIDENCE": Decimal("0.0100"),
    },
    AnomalyMode.ADVERSARIAL: {
        "AMOUNT_MISMATCH": Decimal("0.1000"),
        "MISSING_SETTLEMENT": Decimal("0.0700"),
        "DUPLICATE_PAYMENT": Decimal("0.0500"),
        "FEE_MISMATCH": Decimal("0.0600"),
        "REFUND_MISMATCH": Decimal("0.0400"),
        "PARTIAL_SETTLEMENT": Decimal("0.0500"),
        "TIMING_MISMATCH": Decimal("0.0600"),
        "CURRENCY_MISMATCH": Decimal("0.0200"),
        "ENTITY_LINK_FAILURE": Decimal("0.0200"),
        "CONFLICTING_EVIDENCE": Decimal("0.0200"),
    },
    AnomalyMode.CHAOS: {
        "AMOUNT_MISMATCH": Decimal("0.1200"),
        "MISSING_SETTLEMENT": Decimal("0.0800"),
        "DUPLICATE_PAYMENT": Decimal("0.0600"),
        "FEE_MISMATCH": Decimal("0.0800"),
        "REFUND_MISMATCH": Decimal("0.0600"),
        "PARTIAL_SETTLEMENT": Decimal("0.0600"),
        "TIMING_MISMATCH": Decimal("0.0800"),
        "CURRENCY_MISMATCH": Decimal("0.0300"),
        "ENTITY_LINK_FAILURE": Decimal("0.0300"),
        "CONFLICTING_EVIDENCE": Decimal("0.0400"),
    },
}


class PromptUnderstandingError(ValueError):
    pass


class DeterministicPromptParser:
    def parse(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        text = prompt.strip()
        lowered = text.lower()
        mode = self._mode(lowered)
        record_count = self._record_count(lowered)
        fee_rate = self._fee_rate(lowered)
        gst_rate = self._gst_rate(lowered)
        settlement_days = self._settlement_days(lowered)
        payment_methods = self._payment_methods(lowered)
        currencies = self._currencies(lowered)
        merchant_name = self._merchant_name(lowered)
        refund_rate = Decimal("0.0800")
        if "refund" in lowered and "10%" in lowered:
            refund_rate = Decimal("0.1000")
        anomaly_rates = dict(DEFAULT_ANOMALIES[mode])
        anomaly_rates.update(self._explicit_anomaly_rates(lowered))

        spec = FinancialWorldSpec(
            prompt=text,
            world_name=merchant_name,
            merchant_name=merchant_name,
            record_count=record_count,
            seed=seed,
            currencies=currencies,
            payment_methods=payment_methods,
            fee_rate=fee_rate,
            gst_rate=gst_rate,
            fixed_fee=Decimal("0.00"),
            settlement_delay_days=settlement_days,
            refund_rate=refund_rate,
            partial_settlement_rate=anomaly_rates.get("PARTIAL_SETTLEMENT", Decimal("0.0300")),
            anomaly_mode=mode,
            anomaly_rates=anomaly_rates,
            understanding_source="deterministic_parser",
        )
        steps = [
            UnderstandingStep(
                step="Understand intent",
                detail="Parsed merchant, volume, payment rails, fees, settlement policy and anomaly intent.",
                metadata={
                    "execution_mode": DETERMINISTIC,
                    "provider": "deterministic",
                    "model": "financial-world-parser",
                    "success": True,
                },
            ),
            UnderstandingStep(step="Extract financial entities", detail="MERCHANT, ORDER, PAYMENT, SETTLEMENT, REFUND and FEE_RULE selected."),
            UnderstandingStep(step="Build schema", detail="Canonical Auditra finance schema prepared for preview."),
            UnderstandingStep(step="Build relationship model", detail="Order-payment-settlement-refund-fee relationships derived."),
            UnderstandingStep(step="Configure rules", detail=f"{self._percent(spec.fee_rate)} fee + {self._percent(spec.gst_rate)} GST, T+{spec.settlement_delay_days}, {self._mode_value(spec.anomaly_mode)} anomaly mode."),
        ]
        return spec, steps

    def _record_count(self, text: str) -> int:
        matches = re.findall(r"(\d{2,6})\s*(?:orders|records|transactions|payments)", text)
        if matches:
            return min(10000, max(10, int(matches[0])))
        return 500

    def _fee_rate(self, text: str) -> Decimal:
        match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:platform\s*)?(?:fee|fees|commission)", text)
        if not match:
            match = re.search(r"(?:fee|fees|commission).*?(\d+(?:\.\d+)?)\s*%", text)
        if not match:
            return Decimal("0.0200")
        return rate(Decimal(match.group(1)) / Decimal("100"))

    def _gst_rate(self, text: str) -> Decimal:
        match = re.search(r"(?:gst|tax).*?(\d+(?:\.\d+)?)\s*%", text)
        if not match:
            return Decimal("0.1800")
        return rate(Decimal(match.group(1)) / Decimal("100"))

    def _settlement_days(self, text: str) -> int:
        match = re.search(r"t\s*\+\s*(\d+)", text)
        if match:
            return min(30, int(match.group(1)))
        return 2

    def _payment_methods(self, text: str) -> List[str]:
        methods = []
        if "upi" in text:
            methods.append("UPI")
        if "card" in text or "cards" in text:
            methods.append("CARD")
        if "wallet" in text:
            methods.append("WALLET")
        if "netbanking" in text or "net banking" in text:
            methods.append("NETBANKING")
        return methods or ["UPI", "CARD"]

    def _currencies(self, text: str) -> List[str]:
        currencies = []
        if "inr" in text or "indian" in text or "india" in text:
            currencies.append("INR")
        if "usd" in text:
            currencies.append("USD")
        if "eur" in text:
            currencies.append("EUR")
        return currencies or ["INR"]

    def _mode(self, text: str) -> AnomalyMode:
        if "chaos" in text:
            return AnomalyMode.CHAOS
        if "adversarial" in text or "break" in text:
            return AnomalyMode.ADVERSARIAL
        if "stress" in text or "stressed" in text or "anomal" in text or "partial settlement" in text:
            return AnomalyMode.STRESSED
        return AnomalyMode.NORMAL

    def _merchant_name(self, text: str) -> str:
        if "marketplace" in text:
            return "Auditra Marketplace India"
        if "e-commerce" in text or "ecommerce" in text or "commerce" in text:
            return "Demo Commerce India"
        if "saas" in text:
            return "Nila SaaS Demo"
        return "Demo Commerce India"

    def _explicit_anomaly_rates(self, text: str) -> Dict[str, Decimal]:
        patterns = {
            "AMOUNT_MISMATCH": r"amount mismatch(?:es)?[:\s]+(\d+(?:\.\d+)?)\s*%",
            "MISSING_SETTLEMENT": r"missing settlement(?:s)?[:\s]+(\d+(?:\.\d+)?)\s*%",
            "DUPLICATE_PAYMENT": r"duplicate(?:s| payments)?[:\s]+(\d+(?:\.\d+)?)\s*%",
            "FEE_MISMATCH": r"fee anomal(?:y|ies|ies)[:\s]+(\d+(?:\.\d+)?)\s*%",
        }
        rates: Dict[str, Decimal] = {}
        for name, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                rates[name] = rate(Decimal(match.group(1)) / Decimal("100"))
        return rates

    def _percent(self, value: Decimal) -> str:
        return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"

    def _mode_value(self, value: AnomalyMode | str) -> str:
        return value.value if isinstance(value, AnomalyMode) else str(value)


class LLMWorldSpecProvider:
    prompt_version = "world-spec-v2"
    provider_label = "openai"
    execution_mode = REAL_OPENAI_AI

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.model = self.llm_provider.config.model

    def parse(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        last_error: Optional[Exception] = None
        deterministic_spec, _ = DeterministicPromptParser().parse(prompt, seed=seed)
        for _ in range(2):
            try:
                response = self.llm_provider.generate_structured(
                    schema_name="FinancialWorldSpec",
                    schema=FinancialWorldSpec.model_json_schema(),
                    system_prompt=(
                        "Convert the user prompt into a valid Auditra FinancialWorldSpec JSON object. "
                        "Do not generate financial records. The record generator remains deterministic. "
                        "Respect explicit numeric constraints from input_constraints. Use decimal rates such as 0.0200. "
                        "Use only canonical anomaly names: AMOUNT_MISMATCH, MISSING_SETTLEMENT, DUPLICATE_PAYMENT, "
                        "FEE_MISMATCH, REFUND_MISMATCH, PARTIAL_SETTLEMENT, TIMING_MISMATCH, CURRENCY_MISMATCH, "
                        "CONFLICTING_EVIDENCE, ENTITY_LINK_FAILURE."
                    ),
                    user_payload={
                        "prompt": prompt,
                        "seed": seed,
                        "input_constraints": {
                            "record_count": deterministic_spec.record_count,
                            "fee_rate": str(deterministic_spec.fee_rate),
                            "gst_rate": str(deterministic_spec.gst_rate),
                            "settlement_delay_days": deterministic_spec.settlement_delay_days,
                            "currencies": deterministic_spec.currencies,
                            "payment_methods": deterministic_spec.payment_methods,
                        },
                    },
                )
                parsed = self._normalize_spec_fields(dict(response.output))
                if re.search(r"\d{2,6}\s*(?:orders|records|transactions|payments)", prompt.lower()):
                    parsed["record_count"] = deterministic_spec.record_count
                parsed.setdefault("prompt", prompt)
                parsed.setdefault("seed", seed)
                parsed["understanding_source"] = f"{self.provider_label}:{response.model}"
                spec = FinancialWorldSpec.model_validate(parsed)
                trace = {
                    "execution_mode": self.execution_mode,
                    "provider": response.provider,
                    "model": response.model,
                    "prompt_version": self.prompt_version,
                    "timestamp": response.timestamp,
                    "latency_ms": response.latency_ms,
                    "attempts": response.attempts,
                    "llm_calls": response.llm_calls,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "cost_usd": str(response.estimated_cost_usd) if response.estimated_cost_usd is not None else None,
                    "success": True,
                    "failure_type": None,
                    "response_id": response.response_id,
                }
                steps = [
                    UnderstandingStep(
                        step="Understand intent",
                        detail=f"{response.provider} model {response.model} produced a validated world specification.",
                        metadata=trace,
                    ),
                    UnderstandingStep(step="Validate structured output", detail="Pydantic schema validation passed before deterministic generation."),
                    UnderstandingStep(
                        step="Record AI usage",
                        detail=(
                            f"calls={response.llm_calls}, input_tokens={response.input_tokens}, "
                            f"output_tokens={response.output_tokens}, cost_usd={response.estimated_cost_usd}"
                        ),
                        metadata=trace,
                    ),
                ]
                return spec, steps
            except (LLMInvalidResponse, ValidationError, ValueError) as exc:
                last_error = exc
            except LLMUnavailable as exc:
                raise PromptUnderstandingError(f"{self.provider_label} world builder unavailable: {exc}") from exc
        raise PromptUnderstandingError(f"{self.provider_label} returned invalid FinancialWorldSpec: {last_error}")



    def _normalize_spec_fields(self, parsed: Dict[str, object]) -> Dict[str, object]:
        aliases = {
            "AMOUNT": "AMOUNT_MISMATCH",
            "AMOUNT_MISMATCHES": "AMOUNT_MISMATCH",
            "MISSING": "MISSING_SETTLEMENT",
            "DUPLICATE": "DUPLICATE_PAYMENT",
            "DUPLICATES": "DUPLICATE_PAYMENT",
            "DUPLICATE_PAYMENTS": "DUPLICATE_PAYMENT",
            "FEE": "FEE_MISMATCH",
            "FEE_DISCREPANCY": "FEE_MISMATCH",
            "REFUND": "REFUND_MISMATCH",
            "REFUND_MISMATCHES": "REFUND_MISMATCH",
            "PARTIAL": "PARTIAL_SETTLEMENT",
            "TIMING": "TIMING_MISMATCH",
            "TIMING_ISSUE": "TIMING_MISMATCH",
            "TIMING_ISSUES": "TIMING_MISMATCH",
            "CURRENCY": "CURRENCY_MISMATCH",
            "ENTITY_LINK": "ENTITY_LINK_FAILURE",
            "LINK_FAILURE": "ENTITY_LINK_FAILURE",
        }
        raw_rates = parsed.get("anomaly_rates")
        if isinstance(raw_rates, dict):
            normalized = {}
            for key, value in raw_rates.items():
                canonical = str(key).strip().upper().replace(" ", "_").replace("-", "_")
                canonical = aliases.get(canonical, canonical)
                normalized[canonical] = value
            parsed["anomaly_rates"] = normalized
        return parsed

class OpenAIWorldSpecProvider(LLMWorldSpecProvider):
    provider_label = "openai"
    execution_mode = REAL_OPENAI_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or OpenAILLMProvider(config=config or LLMProviderConfig.from_env("AUDITRA_WORLD_LLM"))
        )


class GroqWorldSpecProvider(LLMWorldSpecProvider):
    provider_label = "groq"
    execution_mode = REAL_GROQ_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or GroqLLMProvider(config=config or LLMProviderConfig.from_groq_env("AUDITRA_WORLD_LLM"))
        )


class GeminiWorldSpecProvider(LLMWorldSpecProvider):
    provider_label = "gemini"
    execution_mode = REAL_GEMINI_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or GeminiLLMProvider(config=config or LLMProviderConfig.from_gemini_env("AUDITRA_WORLD_LLM"))
        )


class OpenRouterWorldSpecProvider(LLMWorldSpecProvider):
    provider_label = "openrouter"
    execution_mode = REAL_OPENROUTER_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or OpenRouterLLMProvider(config=config or LLMProviderConfig.from_openrouter_env("AUDITRA_WORLD_LLM"))
        )


class HuggingFaceWorldSpecProvider(LLMWorldSpecProvider):
    provider_label = "huggingface"
    execution_mode = REAL_HUGGINGFACE_AI

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(
            llm_provider
            or HuggingFaceLLMProvider(config=config or LLMProviderConfig.from_huggingface_env("AUDITRA_WORLD_LLM"))
        )

class WorldUnderstandingService:
    def __init__(
        self,
        openai: Optional[OpenAIWorldSpecProvider] = None,
        groq: Optional[GroqWorldSpecProvider] = None,
        gemini: Optional[GeminiWorldSpecProvider] = None,
        openrouter: Optional[OpenRouterWorldSpecProvider] = None,
        huggingface: Optional[HuggingFaceWorldSpecProvider] = None,
    ):
        self.parser = DeterministicPromptParser()
        self.openai = openai or OpenAIWorldSpecProvider()
        self.groq = groq or GroqWorldSpecProvider()
        self.gemini = gemini or GeminiWorldSpecProvider()
        self.openrouter = openrouter or OpenRouterWorldSpecProvider()
        self.huggingface = huggingface or HuggingFaceWorldSpecProvider()

    def understand(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        provider = resolve_llm_provider("WORLD")
        providers = {
            "groq": self.groq,
            "gemini": self.gemini,
            "openrouter": self.openrouter,
            "huggingface": self.huggingface,
            "openai": self.openai,
        }
        selected = providers.get(provider)
        if selected is not None:
            try:
                return selected.parse(prompt, seed=seed)
            except PromptUnderstandingError as exc:
                spec, steps = self.parser.parse(prompt, seed=seed)
                source = getattr(exc, "__cause__", None) or exc
                failure_type = getattr(source, "failure_type", "invalid_structured_output")
                spec = spec.model_copy(update={"understanding_source": f"deterministic_fallback:{provider}:{failure_type}"})
                steps.insert(
                    0,
                    UnderstandingStep(
                        step="External AI fallback",
                        status="WARNING",
                        detail=f"{provider} could not return a valid spec; deterministic parsing completed the request.",
                        metadata={
                            "execution_mode": OFFLINE_AI,
                            "provider": "deterministic",
                            "model": "financial-world-parser",
                            "prompt_version": selected.prompt_version,
                            "timestamp": getattr(source, "timestamp", None),
                            "latency_ms": getattr(source, "latency_ms", 0.0),
                            "attempts": getattr(source, "attempts", 0),
                            "llm_calls": 0,
                            "input_tokens": None,
                            "output_tokens": None,
                            "total_tokens": None,
                            "cost_usd": None,
                            "success": False,
                            "failure_type": failure_type,
                            "requested_provider": provider,
                        },
                    ),
                )
                return spec, steps
        if provider in {"anthropic", "ollama"}:
            spec, steps = self.parser.parse(prompt, seed=seed)
            spec = spec.model_copy(update={"understanding_source": f"deterministic_fallback:{provider}:provider_not_integrated"})
            steps.insert(
                0,
                UnderstandingStep(
                    step="External AI fallback",
                    status="WARNING",
                    detail=f"{provider} is architecturally supported but not integrated; deterministic parsing completed the request.",
                    metadata={
                        "execution_mode": OFFLINE_AI,
                        "provider": "deterministic",
                        "model": "financial-world-parser",
                        "prompt_version": "world-spec-v2",
                        "timestamp": None,
                        "latency_ms": 0.0,
                        "attempts": 0,
                        "llm_calls": 0,
                        "input_tokens": None,
                        "output_tokens": None,
                        "total_tokens": None,
                        "cost_usd": None,
                        "success": False,
                        "failure_type": "provider_not_integrated",
                        "requested_provider": provider,
                    },
                ),
            )
            return spec, steps
        return self.parser.parse(prompt, seed=seed)
