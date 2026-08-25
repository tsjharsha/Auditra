from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional

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
    currencies: List[str] = Field(default_factory=lambda: ["INR"])
    payment_methods: List[str] = Field(default_factory=lambda: ["UPI", "CARD"])
    fee_rate: Decimal = Decimal("0.0200")
    fixed_fee: Decimal = Decimal("0.00")
    settlement_delay_days: int = Field(default=2, ge=0, le=30)
    refund_rate: Decimal = Decimal("0.0800")
    partial_settlement_rate: Decimal = Decimal("0.0300")
    anomaly_mode: AnomalyMode = AnomalyMode.STRESSED
    anomaly_rates: Dict[str, Decimal] = Field(default_factory=dict)
    temporal_rules: Dict[str, Any] = Field(default_factory=dict)
    relationships: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    start_at: datetime = Field(default_factory=lambda: datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc))
    source: str = "prompt"
    understanding_source: str = "deterministic_parser"
    version: int = 1

    @field_validator("currencies", "payment_methods")
    @classmethod
    def normalize_tokens(cls, value: List[str]) -> List[str]:
        normalized = [str(item).strip().upper() for item in value if str(item).strip()]
        return list(dict.fromkeys(normalized)) or ["INR"]

    @field_validator("currencies")
    @classmethod
    def validate_currencies(cls, value: List[str]) -> List[str]:
        unsupported = sorted(set(value) - SUPPORTED_CURRENCIES)
        if unsupported:
            raise ValueError(f"unsupported currencies: {', '.join(unsupported)}")
        return value

    @field_validator("payment_methods")
    @classmethod
    def validate_payment_methods(cls, value: List[str]) -> List[str]:
        unsupported = sorted(set(value) - SUPPORTED_PAYMENT_METHODS)
        if unsupported:
            raise ValueError(f"unsupported payment methods: {', '.join(unsupported)}")
        return value

    @field_validator("fee_rate", "refund_rate", "partial_settlement_rate")
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
    def normalize_anomaly_rates(cls, value: Dict[str, Decimal]) -> Dict[str, Decimal]:
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
    fields: List[SchemaField]


class SchemaPreview(AuditraModel):
    entities: List[EntitySchema]


class RelationshipEdge(AuditraModel):
    source: str
    relationship: str
    target: str
    required: bool = True
    description: str = ""


class RelationshipModel(AuditraModel):
    nodes: List[str]
    edges: List[RelationshipEdge]


class UnderstandingStep(AuditraModel):
    step: str
    status: str = "COMPLETED"
    detail: str = ""


class WorldValidationCheck(AuditraModel):
    check_id: str
    status: str
    detail: str
    count: int = 0


class WorldValidationReport(AuditraModel):
    world_id: str
    valid: bool
    checks: List[WorldValidationCheck]


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
    currencies: List[str]
    payment_methods: List[str]
    settlement: str
    fee: str
    anomalies: int
    anomaly_mix: Dict[str, int] = Field(default_factory=dict)

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
    understanding_steps: List[UnderstandingStep]
    validation: WorldValidationReport
    summary: WorldSummary
    dataset_id: str
    dataset: Optional[DatasetBundle] = None


class AdapterIngestionResult(AuditraModel):
    adapter: str
    dataset_id: str
    rows_seen: Dict[str, int]
    rows_loaded: Dict[str, int]
    schema_warnings: List[str] = Field(default_factory=list)
    validation: WorldValidationReport
    dataset: Optional[DatasetBundle] = None
