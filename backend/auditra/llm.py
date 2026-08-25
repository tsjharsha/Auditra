from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, Field, ValidationError

from .models import money


class LLMUnavailable(RuntimeError):
    pass


class LLMInvalidResponse(RuntimeError):
    pass


class LLMStructuredResponse(BaseModel):
    provider: str
    model: str
    output: Dict[str, Any]
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0.00")
    latency_ms: float = 0.0
    attempts: int = 1
    response_id: Optional[str] = None


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str = "offline"
    model: str = "gpt-5-mini"
    temperature: float = 0.0
    max_tokens: int = 1200
    timeout_seconds: float = 30.0
    max_retries: int = 1
    input_cost_per_1m: Decimal = Decimal("0.00")
    output_cost_per_1m: Decimal = Decimal("0.00")

    @classmethod
    def from_env(cls, prefix: str = "AUDITRA_LLM") -> "LLMProviderConfig":
        return cls(
            provider=os.getenv(f"{prefix}_PROVIDER", os.getenv("AUDITRA_LLM_PROVIDER", "offline")),
            model=os.getenv(f"{prefix}_MODEL", os.getenv("AUDITRA_OPENAI_MODEL", "gpt-5-mini")),
            temperature=float(os.getenv(f"{prefix}_TEMPERATURE", "0")),
            max_tokens=int(os.getenv(f"{prefix}_MAX_TOKENS", "1200")),
            timeout_seconds=float(os.getenv(f"{prefix}_TIMEOUT", "30")),
            max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", "1")),
            input_cost_per_1m=Decimal(os.getenv(f"{prefix}_INPUT_COST_PER_1M", "0.00")),
            output_cost_per_1m=Decimal(os.getenv(f"{prefix}_OUTPUT_COST_PER_1M", "0.00")),
        )


class LLMProvider:
    provider_name = "base"

    def __init__(self, config: Optional[LLMProviderConfig] = None):
        self.config = config or LLMProviderConfig()

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        raise NotImplementedError


class OfflineProvider(LLMProvider):
    provider_name = "offline"

    def __init__(self, output: Optional[Dict[str, Any]] = None, config: Optional[LLMProviderConfig] = None):
        super().__init__(config or LLMProviderConfig(provider="offline", model="offline-structured"))
        self.output = output or {}

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        return LLMStructuredResponse(
            provider=self.provider_name,
            model=self.config.model,
            output=dict(self.output),
            llm_calls=0,
            estimated_cost_usd=Decimal("0.00"),
            latency_ms=0.0,
            attempts=0,
        )


class MockProvider(LLMProvider):
    provider_name = "mock"

    def __init__(
        self,
        responses: Optional[List[Dict[str, Any]]] = None,
        failures_before_success: int = 0,
        malformed_before_success: int = 0,
        config: Optional[LLMProviderConfig] = None,
    ):
        super().__init__(config or LLMProviderConfig(provider="mock", model="mock-model"))
        self.responses = responses or [{}]
        self.failures_before_success = failures_before_success
        self.malformed_before_success = malformed_before_success
        self.calls = 0

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        self.calls += 1
        if self.failures_before_success > 0:
            self.failures_before_success -= 1
            raise LLMUnavailable("mock provider unavailable")
        output = {"malformed": True} if self.malformed_before_success > 0 else self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if self.malformed_before_success > 0:
            self.malformed_before_success -= 1
        return LLMStructuredResponse(
            provider=self.provider_name,
            model=self.config.model,
            output=dict(output),
            llm_calls=1,
            input_tokens=123,
            output_tokens=45,
            estimated_cost_usd=Decimal("0.01"),
            latency_ms=1.0,
            attempts=1,
            response_id=f"mock-{self.calls}",
        )


class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, config: Optional[LLMProviderConfig] = None):
        super().__init__(config or LLMProviderConfig.from_env())
        self.config = LLMProviderConfig(
            provider="openai",
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout_seconds=self.config.timeout_seconds,
            max_retries=self.config.max_retries,
            input_cost_per_1m=self.config.input_cost_per_1m,
            output_cost_per_1m=self.config.output_cost_per_1m,
        )

    def generate_structured(
        self,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> LLMStructuredResponse:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMUnavailable("OPENAI_API_KEY is not configured")
        last_error: Optional[Exception] = None
        attempts = max(1, self.config.max_retries + 1)
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                payload = self._request(api_key, schema_name, schema, system_prompt, user_payload)
                output = self._extract_output(payload)
                usage = payload.get("usage", {})
                input_tokens = int(usage.get("input_tokens", 0))
                output_tokens = int(usage.get("output_tokens", 0))
                return LLMStructuredResponse(
                    provider=self.provider_name,
                    model=self.config.model,
                    output=output,
                    llm_calls=1,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    estimated_cost_usd=self._estimate_cost(input_tokens, output_tokens),
                    latency_ms=round((time.perf_counter() - started) * 1000, 4),
                    attempts=attempt,
                    response_id=payload.get("id"),
                )
            except (json.JSONDecodeError, LLMInvalidResponse, urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                time.sleep(min(0.5 * attempt, 2.0))
        raise LLMUnavailable(f"OpenAI structured response failed: {last_error}")

    def _request(
        self,
        api_key: str,
        schema_name: str,
        schema: Dict[str, Any],
        system_prompt: str,
        user_payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, default=str)},
            ],
            "max_output_tokens": self.config.max_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name[:64],
                    "schema": schema,
                    "strict": False,
                }
            },
        }
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _extract_output(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if payload.get("status") not in (None, "completed"):
            raise LLMInvalidResponse(f"response status was {payload.get('status')}")
        if payload.get("output_text"):
            return json.loads(payload["output_text"])
        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return json.loads(text)
        raise LLMInvalidResponse("missing structured output text")

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        input_cost = (Decimal(input_tokens) / Decimal("1000000")) * self.config.input_cost_per_1m
        output_cost = (Decimal(output_tokens) / Decimal("1000000")) * self.config.output_cost_per_1m
        return money(input_cost + output_cost)


def validate_structured_output(model_type: type[BaseModel], response: LLMStructuredResponse) -> BaseModel:
    try:
        return model_type.model_validate(response.output)
    except ValidationError as exc:
        raise LLMInvalidResponse(str(exc)) from exc
