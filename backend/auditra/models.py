from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


MONEY_QUANT = Decimal("0.01")


def money(value: Any) -> Decimal:
    """Return a two-decimal Decimal for financial arithmetic."""
    if isinstance(value, Decimal):
        raw = value
    else:
        raw = Decimal(str(value))
    return raw.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuditraModel(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_encoders={Decimal: str, datetime: lambda value: value.isoformat()},
    )


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    FEE_EXPLAINED = "FEE_EXPLAINED"
    REFUND_ADJUSTED = "REFUND_ADJUSTED"
    DUPLICATE = "DUPLICATE"
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    TIMING_MISMATCH = "TIMING_MISMATCH"
    UNRESOLVED = "UNRESOLVED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    REVIEW = "REVIEW"
    LOW = "LOW"


class ScenarioMode(str, Enum):
    NORMAL = "NORMAL"
    MIXED = "MIXED"
    DIFFICULT = "DIFFICULT"
    ADVERSARIAL = "ADVERSARIAL"


class ReviewAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MARK_UNRESOLVED = "MARK_UNRESOLVED"


class InvariantStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class HypothesisStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class SourceRecord(AuditraModel):
    source: str
    source_record_id: str
    ingested_at: datetime = Field(default_factory=now_utc)
    original: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("ingested_at")
    @classmethod
    def require_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class Merchant(SourceRecord):
    merchant_id: str
    name: str
    settlement_cycle_days: int = 2
    risk_tier: str = "standard"


class Order(SourceRecord):
    order_id: str
    merchant_id: str
    customer_id: str
    amount: Decimal
    currency: str = "INR"
    created_at: datetime
    invoice_id: Optional[str] = None
    reference_id: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def quantize_amount(cls, value: Decimal) -> Decimal:
        return money(value)

    @field_validator("created_at")
    @classmethod
    def require_created_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class Payment(SourceRecord):
    payment_id: str
    order_id: Optional[str]
    merchant_id: str
    customer_id: str
    amount: Decimal
    currency: str = "INR"
    captured_at: datetime
    payment_method: str = "upi"
    reference_id: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def quantize_amount(cls, value: Decimal) -> Decimal:
        return money(value)

    @field_validator("captured_at")
    @classmethod
    def require_captured_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class Settlement(SourceRecord):
    settlement_id: str
    payment_id: str
    merchant_id: str
    amount: Decimal
    currency: str = "INR"
    settled_at: datetime
    batch_id: str

    @field_validator("amount")
    @classmethod
    def quantize_amount(cls, value: Decimal) -> Decimal:
        return money(value)

    @field_validator("settled_at")
    @classmethod
    def require_settled_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class Refund(SourceRecord):
    refund_id: str
    payment_id: str
    merchant_id: str
    amount: Decimal
    currency: str = "INR"
    refunded_at: datetime
    reason: str = "customer_request"

    @field_validator("amount")
    @classmethod
    def quantize_amount(cls, value: Decimal) -> Decimal:
        value = money(value)
        if value < 0:
            raise ValueError("refund amount cannot be negative")
        return value

    @field_validator("refunded_at")
    @classmethod
    def require_refunded_tz(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value


class FeeRule(SourceRecord):
    fee_rule_id: str
    merchant_id: str
    currency: str = "INR"
    percent_bps: int = 200
    fixed_fee: Decimal = Decimal("3.00")
    gst_bps: int = 1800
    active_from: datetime
    active_to: Optional[datetime] = None

    @field_validator("fixed_fee")
    @classmethod
    def quantize_fee(cls, value: Decimal) -> Decimal:
        value = money(value)
        if value < 0:
            raise ValueError("fixed fee cannot be negative")
        return value

    @field_validator("percent_bps", "gst_bps")
    @classmethod
    def validate_basis_points(cls, value: int) -> int:
        if value < 0 or value > 10000:
            raise ValueError("basis points must be between 0 and 10000")
        return value

    @field_validator("active_from", "active_to")
    @classmethod
    def require_active_tz(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return value
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return value

    def applies_at(self, timestamp: datetime) -> bool:
        if timestamp < self.active_from:
            return False
        if self.active_to and timestamp >= self.active_to:
            return False
        return True

    def calculate_fee(self, amount: Decimal) -> Decimal:
        percentage = (money(amount) * Decimal(self.percent_bps)) / Decimal(10000)
        return money(percentage + self.fixed_fee)


    def calculate_gst(self, fee: Decimal) -> Decimal:
        return money(money(fee) * Decimal(self.gst_bps) / Decimal(10000))

class EvidenceItem(AuditraModel):
    evidence_id: str
    entity_type: str
    entity_id: str
    source: str
    summary: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class GraphNode(AuditraModel):
    id: str
    type: str
    label: str
    evidence_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(AuditraModel):
    id: str
    source: str
    target: str
    relationship: str
    confidence: float
    evidence_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class EvidenceGraph(AuditraModel):
    transaction_id: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class AuditEvent(AuditraModel):
    event_id: str
    timestamp: datetime = Field(default_factory=now_utc)
    actor: str
    action: str
    entity: str
    entity_id: str
    inputs_ref: Dict[str, Any] = Field(default_factory=dict)
    output_ref: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    correlation_id: str


class AgentToolCall(AuditraModel):
    call_id: str
    run_id: str
    case_id: str
    tool_name: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    started_at: datetime
    finished_at: datetime
    success: bool = True
    duration_ms: float = 0.0
    result_size_bytes: int = 0
    error_type: Optional[str] = None


class VerificationResult(AuditraModel):
    decision_status: ReconciliationStatus
    passed: bool
    challenges: List[str] = Field(default_factory=list)
    checks: List[Dict[str, Any]] = Field(default_factory=list)


class InvariantResult(AuditraModel):
    rule_id: str
    status: InvariantStatus
    expected: Optional[Decimal] = None
    actual: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    evidence_ids: List[str] = Field(default_factory=list)
    reason: str = ""
    severity: str = "info"

    @field_validator("expected", "actual", "difference")
    @classmethod
    def quantize_invariant_money(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return value
        return money(value)


class InvestigationHypothesis(AuditraModel):
    hypothesis_id: str
    label: str
    status: HypothesisStatus = HypothesisStatus.INCONCLUSIVE
    confidence: float = 0.0
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    tool_call_ids: List[str] = Field(default_factory=list)
    verification_checks: List[Dict[str, Any]] = Field(default_factory=list)
    rationale: str = ""


class AIInvestigationResult(AuditraModel):
    investigation_id: str
    payment_id: str
    case_id: Optional[str] = None
    objective: str = ""
    provider: str = "offline_structured"
    model: str = "auditra-hypothesis-agent-v1"
    mode: str = "ai_assisted"
    prompt_version: str = "investigation-plan-v2"
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    llm_calls: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[Decimal] = Decimal("0.00")
    ai_unavailable: bool = False
    provider_error: Optional[str] = None
    fallback_reason: Optional[str] = None
    response_id: Optional[str] = None
    provider_attempts: int = 0
    provider_latency_ms: float = 0.0
    provider_trace: List[Dict[str, Any]] = Field(default_factory=list)
    available_tools: List[str] = Field(default_factory=list)
    verification_requirements: List[str] = Field(default_factory=list)
    max_tool_calls: int = 0
    max_llm_calls: int = 1
    hypotheses: List[InvestigationHypothesis] = Field(default_factory=list)
    selected_hypothesis_id: Optional[str] = None
    recommendation: ReconciliationStatus
    rationale: str = ""
    self_challenge: List[str] = Field(default_factory=list)
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    contradicting_evidence_ids: List[str] = Field(default_factory=list)
    confidence_factors: Dict[str, float] = Field(default_factory=dict)
    negative_factors: Dict[str, float] = Field(default_factory=dict)
    verification_summary: Dict[str, Any] = Field(default_factory=dict)
    escalation_reason: Optional[str] = None
    tool_call_count: int = 0

    @field_validator("estimated_cost_usd")
    @classmethod
    def quantize_ai_cost(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return None
        return money(value)


class ControllerDecision(AuditraModel):
    case_id: str
    payment_id: str
    status: ReconciliationStatus
    confidence_score: float
    confidence_band: ConfidenceBand
    financial_impact: Decimal
    expected_settlement: Optional[Decimal] = None
    actual_settlement: Optional[Decimal] = None
    expected_fee: Optional[Decimal] = None
    expected_gst: Optional[Decimal] = None
    refund_total: Decimal = Decimal("0.00")
    difference: Optional[Decimal] = None
    reason_codes: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    confidence_factors: Dict[str, float] = Field(default_factory=dict)
    risk_score: float = 0.0
    risk_factors: List[str] = Field(default_factory=list)
    invariants: List[InvariantResult] = Field(default_factory=list)
    ai_investigation: Optional[AIInvestigationResult] = None
    verification: Optional[VerificationResult] = None

    @field_validator("financial_impact", "expected_settlement", "actual_settlement", "expected_fee", "expected_gst", "refund_total", "difference")
    @classmethod
    def quantize_optional_money(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return value
        return money(value)


class ReconciliationCase(AuditraModel):
    case_id: str
    run_id: str
    payment_id: str
    order_id: Optional[str] = None
    merchant_id: str
    status: ReconciliationStatus
    decision: ControllerDecision
    graph: EvidenceGraph
    evidence: List[EvidenceItem] = Field(default_factory=list)
    tool_calls: List[AgentToolCall] = Field(default_factory=list)
    invariants: List[InvariantResult] = Field(default_factory=list)
    ai_investigation: Optional[AIInvestigationResult] = None
    risk_score: float = 0.0
    risk_factors: List[str] = Field(default_factory=list)
    investigation_timeline: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now_utc)


class GroundTruthCase(AuditraModel):
    payment_id: str
    expected_status: ReconciliationStatus
    scenario: str
    financial_impact: Decimal = Decimal("0.00")
    reason: str

    @field_validator("financial_impact")
    @classmethod
    def quantize_impact(cls, value: Decimal) -> Decimal:
        return money(value)


class DatasetBundle(AuditraModel):
    dataset_id: str
    mode: ScenarioMode
    seed: int
    requested_records: int
    generated_at: datetime = Field(default_factory=now_utc)
    merchants: List[Merchant]
    orders: List[Order]
    payments: List[Payment]
    settlements: List[Settlement]
    refunds: List[Refund]
    fee_rules: List[FeeRule]
    ground_truth: Dict[str, GroundTruthCase] = Field(default_factory=dict)


class ScenarioRequest(AuditraModel):
    mode: ScenarioMode = ScenarioMode.MIXED
    record_count: int = Field(default=1000, ge=10, le=10000)
    seed: int = 42


class RunMetrics(AuditraModel):
    transactions_processed: int
    total_payment_volume: Decimal
    reconciled_amount: Decimal
    normalization_ms: float = 0.0
    ai_investigation_ms: float = 0.0
    match_rate: float
    automatic_resolution_rate: float
    exception_rate: float
    unresolved_rate: float
    human_review_rate: float
    throughput_records_per_sec: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float = 0.0
    ai_investigation_count: int = 0
    llm_calls: int = 0
    agent_tool_calls: int = 0
    estimated_ai_cost_usd: Decimal = Decimal("0.00")
    ai_invocation_rate: float = 0.0
    average_risk_score: float = 0.0

    @field_validator("total_payment_volume", "reconciled_amount", "estimated_ai_cost_usd")
    @classmethod
    def quantize_totals(cls, value: Decimal) -> Decimal:
        return money(value)


class FailureRecord(AuditraModel):
    case_id: str
    payment_id: str
    expected: ReconciliationStatus
    predicted: ReconciliationStatus
    root_cause: str
    evidence_available: List[str] = Field(default_factory=list)
    failure_category: str
    financial_impact: Decimal = Decimal("0.00")

    @field_validator("financial_impact")
    @classmethod
    def quantize_failure_impact(cls, value: Decimal) -> Decimal:
        return money(value)


class EvaluationMetrics(AuditraModel):
    accuracy: float
    precision: float
    recall: float
    f1: float
    false_positive_rate: float
    false_negative_rate: float
    # Explicit names make the binary exception-detection meaning visible to API consumers.
    # The legacy names are retained for backward-compatible reports.
    exception_false_positive_rate: float = 0.0
    exception_false_negative_rate: float = 0.0
    match_rate: float
    automatic_resolution_rate: float
    escalation_rate: float
    unresolved_rate: float
    throughput_records_per_sec: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float = 0.0
    llm_calls: int = 0
    agent_tool_calls: int = 0
    estimated_ai_cost_usd: Decimal = Decimal("0.00")
    financial_amount_correctly_reconciled: Decimal
    financial_amount_incorrectly_classified: Decimal
    financial_impact_of_errors: Decimal
    confusion_matrix: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    class_metrics: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    failure_taxonomy: Dict[str, int] = Field(default_factory=dict)

    @field_validator(
        "financial_amount_correctly_reconciled",
        "financial_amount_incorrectly_classified",
        "financial_impact_of_errors",
        "estimated_ai_cost_usd",
    )
    @classmethod
    def quantize_eval_money(cls, value: Decimal) -> Decimal:
        return money(value)


class ControllerRun(AuditraModel):
    run_id: str
    dataset_id: str
    started_at: datetime
    finished_at: datetime
    duration_ms: float
    metrics: RunMetrics
    cases: List[ReconciliationCase]
    audit_events: List[AuditEvent] = Field(default_factory=list)


class EvaluationRun(AuditraModel):
    evaluation_run_id: str
    controller_run_id: str
    dataset_id: str
    created_at: datetime = Field(default_factory=now_utc)
    metrics: EvaluationMetrics
    failures: List[FailureRecord] = Field(default_factory=list)


class ReviewRequest(AuditraModel):
    action: ReviewAction
    reviewer: str = "human_reviewer"
    note: str = ""
