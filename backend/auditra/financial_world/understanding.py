from __future__ import annotations

import os
import re
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from pydantic import ValidationError

from ..llm import LLMInvalidResponse, LLMProvider, LLMProviderConfig, LLMUnavailable, OpenAIProvider as OpenAILLMProvider
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
            fixed_fee=Decimal("0.00"),
            settlement_delay_days=settlement_days,
            refund_rate=refund_rate,
            partial_settlement_rate=anomaly_rates.get("PARTIAL_SETTLEMENT", Decimal("0.0300")),
            anomaly_mode=mode,
            anomaly_rates=anomaly_rates,
            understanding_source="deterministic_parser",
        )
        steps = [
            UnderstandingStep(step="Understand intent", detail="Parsed merchant, volume, payment rails, fees, settlement policy and anomaly intent."),
            UnderstandingStep(step="Extract financial entities", detail="MERCHANT, ORDER, PAYMENT, SETTLEMENT, REFUND and FEE_RULE selected."),
            UnderstandingStep(step="Build schema", detail="Canonical Auditra finance schema prepared for preview."),
            UnderstandingStep(step="Build relationship model", detail="Order-payment-settlement-refund-fee relationships derived."),
            UnderstandingStep(step="Configure rules", detail=f"{self._percent(spec.fee_rate)} fee, T+{spec.settlement_delay_days}, {self._mode_value(spec.anomaly_mode)} anomaly mode."),
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


class OpenAIWorldSpecProvider:
    prompt_version = "world-spec-v2"

    def __init__(self, llm_provider: Optional[LLMProvider] = None, config: Optional[LLMProviderConfig] = None):
        self.llm_provider = llm_provider or OpenAILLMProvider(config=config or LLMProviderConfig.from_env("AUDITRA_WORLD_LLM"))
        self.model = self.llm_provider.config.model

    def parse(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        last_error: Optional[Exception] = None
        for _ in range(2):
            try:
                response = self.llm_provider.generate_structured(
                    schema_name="FinancialWorldSpec",
                    schema=FinancialWorldSpec.model_json_schema(),
                    system_prompt=(
                        "Convert the user prompt into a valid Auditra FinancialWorldSpec JSON object. "
                        "Do not generate financial records. The record generator remains deterministic. "
                        "Only use supported currencies, payment methods and anomaly names from the schema."
                    ),
                    user_payload={"prompt": prompt, "seed": seed},
                )
                parsed = dict(response.output)
                parsed.setdefault("prompt", prompt)
                parsed.setdefault("seed", seed)
                parsed["understanding_source"] = f"openai:{self.model}"
                spec = FinancialWorldSpec.model_validate(parsed)
                steps = [
                    UnderstandingStep(step="Understand intent", detail=f"LLM provider {self.model} produced a validated world specification."),
                    UnderstandingStep(step="Validate structured output", detail="Pydantic schema validation passed before deterministic generation."),
                    UnderstandingStep(
                        step="Record AI usage",
                        detail=(
                            f"calls={response.llm_calls}, input_tokens={response.input_tokens}, "
                            f"output_tokens={response.output_tokens}, cost_usd={response.estimated_cost_usd}"
                        ),
                    ),
                ]
                return spec, steps
            except (LLMInvalidResponse, ValidationError, ValueError) as exc:
                last_error = exc
            except LLMUnavailable as exc:
                raise PromptUnderstandingError(f"OpenAI world builder unavailable: {exc}") from exc
        raise PromptUnderstandingError(f"OpenAI returned invalid FinancialWorldSpec: {last_error}")


class WorldUnderstandingService:
    def __init__(self, openai: Optional[OpenAIWorldSpecProvider] = None):
        self.parser = DeterministicPromptParser()
        self.openai = openai or OpenAIWorldSpecProvider()

    def understand(self, prompt: str, seed: int = 42) -> Tuple[FinancialWorldSpec, List[UnderstandingStep]]:
        provider = os.getenv("AUDITRA_WORLD_LLM_PROVIDER", os.getenv("AUDITRA_LLM_PROVIDER", "")).lower()
        if os.getenv("AUDITRA_USE_OPENAI_WORLD_BUILDER") == "1" or provider == "openai":
            return self.openai.parse(prompt, seed=seed)
        return self.parser.parse(prompt, seed=seed)
