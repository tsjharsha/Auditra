from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ..models import AuditraModel, DatasetBundle, money

RATE_QUANT = Decimal("0.0001")
SUPPORTED_CURRENCIES = {"INR", "USD", "EUR"}
SUPPORTED_PAYMENT_METHODS = {"UPI", "CARD", "WALLET", "NETBANKING"}
SUPPORTED_ANOMALIES = {
    "AMOUNT_MISMATCH",
    "MISSING_SETTLEMENT",
    "DUPLICATE_PAYMENT",
    "FEE_MISMATCH",
    "REFUND_MISMATCH",
    "PARTIAL_SETTLEMENT",
    "TIMING_MISMATCH",
    "CURRENCY_MISMATCH",
    "CONFLICTING_EVIDENCE",
    "ENTITY_LINK_FAILURE",
}


def rate(value: Any) -> Decimal:
    raw = value if isinstance(value, Decimal) else Decimal(str(value))
    return raw.quantize(RATE_QUANT, rounding=ROUND_HALF_UP)


class AnomalyMode(str, Enum):
    NORMAL = "NORMAL"
    STRESSED = "STRESSED"
    ADVERSARIAL = "ADVERSARIAL"
    CHAOS = "CHAOS"


class FinancialWorldSpec(AuditraModel):
    prompt: str = ""
    world_name: str = "Demo Commerce India"
    merchant_name: str = "Demo Commerce India"
    country: str = "IN"
    record_count: int = Field(default=500, ge=10, le=10000)
    seed: int = 42
    currencies: list[str] = Field(default_factory=lambda: ["INR"])
    payment_methods: list[str] = Field(default_factory=lambda: ["UPI", "CARD"])
    fee_rate: Decimal = Decimal("0.0200")
    gst_rate: Decimal = Decimal("0.1800")
    fixed_fee: Decimal = Decimal("0.00")
    settlement_delay_days: int = Field(default=2, ge=0, le=30)
    refund_rate: Decimal = Decimal("0.0800")
    partial_settlement_rate: Decimal = Decimal("0.0300")
    anomaly_mode: AnomalyMode = AnomalyMode.STRESSED
    anomaly_rates: dict[str, Decimal] = Field(default_factory=dict)
    temporal_rules: dict[str, Any] = Field(default_factory=dict)
    relationships: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    start_at: datetime = Field(default_factory=lambda: datetime(2026, 1, 5, 9, 30, tzinfo=UTC))
    source: str = "prompt"
    understanding_source: str = "deterministic_parser"
    version: int = 1

    @field_validator("currencies", "payment_methods")
    @classmethod
    def normalize_tokens(cls, value: list[str]) -> list[str]:
        normalized = [str(item).strip().upper() for item in value if str(item).strip()]
        return list(dict.fromkeys(normalized)) or ["INR"]

    @field_validator("currencies")
    @classmethod
    def validate_currencies(cls, value: list[str]) -> list[str]:
        unsupported = sorted(set(value) - SUPPORTED_CURRENCIES)
        if unsupported:
            raise ValueError(f"unsupported currencies: {', '.join(unsupported)}")
        return value

    @field_validator("payment_methods")
    @classmethod
    def validate_payment_methods(cls, value: list[str]) -> list[str]:
        unsupported = sorted(set(value) - SUPPORTED_PAYMENT_METHODS)
        if unsupported:
            raise ValueError(f"unsupported payment methods: {', '.join(unsupported)}")
        return value

    @field_validator("fee_rate", "gst_rate", "refund_rate", "partial_settlement_rate")
    @classmethod
    def quantize_rate(cls, value: Decimal) -> Decimal:
        value = rate(value)
        if value < 0:
            raise ValueError("rates cannot be negative")
        if value > Decimal("1.0000"):
            raise ValueError("rates cannot exceed 1.0")
        return value

    @field_validator("fixed_fee")
    @classmethod
    def quantize_fixed_fee(cls, value: Decimal) -> Decimal:
        return money(value)

    @field_validator("start_at")
    @classmethod
    def require_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("start_at must be timezone-aware")
        return value

    @field_validator("anomaly_rates")
    @classmethod
    def normalize_anomaly_rates(cls, value: dict[str, Decimal]) -> dict[str, Decimal]:
        normalized = {str(key).upper(): rate(raw) for key, raw in value.items()}
        unsupported = sorted(set(normalized) - SUPPORTED_ANOMALIES)
        if unsupported:
            raise ValueError(f"unsupported anomaly types: {', '.join(unsupported)}")
        if any(item < 0 for item in normalized.values()):
            raise ValueError("anomaly rates cannot be negative")
        if sum(normalized.values(), Decimal("0.0000")) > Decimal("0.8000"):
            raise ValueError("combined anomaly rates cannot exceed 0.8")
        return normalized


class SchemaField(AuditraModel):
    name: str
    type: str
    required: bool = True
    description: str = ""


class EntitySchema(AuditraModel):
    entity: str
    fields: list[SchemaField]


class SchemaPreview(AuditraModel):
    entities: list[EntitySchema]


class RelationshipEdge(AuditraModel):
    source: str
    relationship: str
    target: str
    required: bool = True
    description: str = ""


class RelationshipModel(AuditraModel):
    nodes: list[str]
    edges: list[RelationshipEdge]


class UnderstandingStep(AuditraModel):
    step: str
    status: str = "COMPLETED"
    detail: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorldValidationCheck(AuditraModel):
    check_id: str
    status: str
    detail: str
    count: int = 0


class WorldValidationReport(AuditraModel):
    world_id: str
    valid: bool
    checks: list[WorldValidationCheck]


class WorldSummary(AuditraModel):
    world_id: str
    world_version: int
    merchant: str
    orders: int
    payments: int
    settlements: int
    refunds: int
    fee_rules: int
    payment_volume: Decimal
    reconciled_amount: Decimal
    unresolved_amount: Decimal
    human_review_amount: Decimal
    currencies: list[str]
    payment_methods: list[str]
    settlement: str
    fee: str
    anomalies: int
    anomaly_mix: dict[str, int] = Field(default_factory=dict)

    @field_validator("payment_volume", "reconciled_amount", "unresolved_amount", "human_review_amount")
    @classmethod
    def quantize_summary_money(cls, value: Decimal) -> Decimal:
        return money(value)


class FinancialWorldBuildResult(AuditraModel):
    world_id: str
    world_version: int
    prompt: str
    spec: FinancialWorldSpec
    schema_preview: SchemaPreview
    relationship_model: RelationshipModel
    understanding_steps: list[UnderstandingStep]
    validation: WorldValidationReport
    summary: WorldSummary
    dataset_id: str
    dataset: DatasetBundle | None = None


class AdapterIngestionResult(AuditraModel):
    adapter: str
    dataset_id: str
    rows_seen: dict[str, int]
    rows_loaded: dict[str, int]
    schema_warnings: list[str] = Field(default_factory=list)
    validation: WorldValidationReport
    dataset: DatasetBundle | None = None
