export type ScenarioMode = "NORMAL" | "MIXED" | "DIFFICULT" | "ADVERSARIAL";

export type AnomalyMode = "NORMAL" | "STRESSED" | "ADVERSARIAL" | "CHAOS";

export type ReconciliationStatus =
  | "MATCHED"
  | "PARTIAL_MATCH"
  | "FEE_EXPLAINED"
  | "REFUND_ADJUSTED"
  | "DUPLICATE"
  | "MISSING_SETTLEMENT"
  | "AMOUNT_MISMATCH"
  | "TIMING_MISMATCH"
  | "UNRESOLVED"
  | "HUMAN_REVIEW";

export type ConfidenceBand = "HIGH" | "MEDIUM" | "REVIEW" | "LOW";

export type ReviewAction = "APPROVE" | "REJECT" | "MARK_UNRESOLVED";

export type PrimitiveRecord = Record<string, unknown> & {
  original?: Record<string, unknown>;
};

export interface FinancialWorldSpec {
  prompt: string;
  world_name: string;
  merchant_name: string;
  country: string;
  record_count: number;
  seed: number;
  currencies: string[];
  payment_methods: string[];
  fee_rate: string;
  fixed_fee: string;
  settlement_delay_days: number;
  refund_rate: string;
  partial_settlement_rate: string;
  anomaly_mode: AnomalyMode;
  anomaly_rates: Record<string, string>;
  temporal_rules: Record<string, unknown>;
  relationships: string[];
  constraints: string[];
  start_at: string;
  source: string;
  understanding_source: string;
  version: number;
}

export interface SchemaField {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export interface EntitySchema {
  entity: string;
  fields: SchemaField[];
}

export interface SchemaPreview {
  entities: EntitySchema[];
}

export interface RelationshipEdge {
  source: string;
  relationship: string;
  target: string;
  required: boolean;
  description: string;
}

export interface RelationshipModel {
  nodes: string[];
  edges: RelationshipEdge[];
}

export interface UnderstandingStep {
  step: string;
  status: string;
  detail: string;
}

export interface WorldSummary {
  world_id: string;
  world_version: number;
  merchant: string;
  orders: number;
  payments: number;
  settlements: number;
  refunds: number;
  fee_rules: number;
  payment_volume: string;
  reconciled_amount: string;
  unresolved_amount: string;
  human_review_amount: string;
  currencies: string[];
  payment_methods: string[];
  settlement: string;
  fee: string;
  anomalies: number;
  anomaly_mix: Record<string, number>;
}

export interface VisibleDataset {
  dataset_id: string;
  mode: ScenarioMode;
  seed: number;
  requested_records: number;
  generated_at: string;
  counts: Record<string, number>;
  records?: {
    merchants: PrimitiveRecord[];
    orders: PrimitiveRecord[];
    payments: PrimitiveRecord[];
    settlements: PrimitiveRecord[];
    refunds: PrimitiveRecord[];
    fee_rules: PrimitiveRecord[];
  };
}

export interface WorldBuildResult {
  world_id: string;
  world_version: number;
  prompt: string;
  spec: FinancialWorldSpec;
  schema_preview: SchemaPreview;
  relationship_model: RelationshipModel;
  understanding_steps: UnderstandingStep[];
  validation: {
    world_id: string;
    valid: boolean;
    checks: Array<{ check_id: string; status: string; detail: string; count: number }>;
  };
  summary: WorldSummary;
  dataset_id: string;
  dataset: VisibleDataset | null;
}

export interface WorldPreview {
  spec: FinancialWorldSpec;
  schema_preview: SchemaPreview;
  relationship_model: RelationshipModel;
  understanding_steps: UnderstandingStep[];
}

export interface RunMetrics {
  transactions_processed: number;
  total_payment_volume: string;
  reconciled_amount: string;
  normalization_ms: number;
  ai_investigation_ms: number;
  match_rate: number;
  automatic_resolution_rate: number;
  exception_rate: number;
  unresolved_rate: number;
  human_review_rate: number;
  throughput_records_per_sec: number;
  median_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  ai_investigation_count: number;
  ai_invocation_rate: number;
  llm_calls: number;
  agent_tool_calls: number;
  estimated_ai_cost_usd: string;
  average_risk_score: number;
}

export interface EvaluationMetrics {
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate: number;
  false_negative_rate: number;
  match_rate: number;
  automatic_resolution_rate: number;
  escalation_rate: number;
  unresolved_rate: number;
  throughput_records_per_sec: number;
  median_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  llm_calls: number;
  agent_tool_calls: number;
  estimated_ai_cost_usd: string;
  financial_amount_correctly_reconciled: string;
  financial_amount_incorrectly_classified: string;
  financial_impact_of_errors: string;
  confusion_matrix: Record<string, Record<string, number>>;
  class_metrics: Record<string, Record<string, number>>;
  failure_taxonomy: Record<string, number>;
}

export interface EvidenceItem {
  evidence_id: string;
  entity_type: string;
  entity_id: string;
  source: string;
  summary: string;
  payload: PrimitiveRecord;
}

export interface AgentToolCall {
  call_id: string;
  run_id: string;
  case_id: string;
  tool_name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  started_at: string;
  finished_at: string;
  success: boolean;
  duration_ms: number;
  result_size_bytes: number;
  error_type?: string | null;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
  evidence_id?: string | null;
  data: Record<string, unknown>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  confidence: number;
  evidence_id?: string | null;
  data: Record<string, unknown>;
}

export interface EvidenceGraph {
  transaction_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface InvestigationHypothesis {
  hypothesis_id: string;
  label: string;
  status: "SUPPORTED" | "REJECTED" | "INCONCLUSIVE";
  confidence: number;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  tool_call_ids: string[];
  verification_checks: Array<Record<string, unknown>>;
  rationale: string;
}

export interface AIInvestigationResult {
  investigation_id: string;
  payment_id: string;
  case_id?: string | null;
  objective: string;
  provider: string;
  model: string;
  mode: string;
  prompt_version: string;
  llm_calls: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: string;
  ai_unavailable: boolean;
  provider_error?: string | null;
  available_tools: string[];
  verification_requirements: string[];
  hypotheses: InvestigationHypothesis[];
  selected_hypothesis_id?: string | null;
  recommendation: ReconciliationStatus;
  rationale: string;
  self_challenge: string[];
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  confidence_factors: Record<string, number>;
  negative_factors: Record<string, number>;
  verification_summary: Record<string, unknown>;
  escalation_reason?: string | null;
  tool_call_count: number;
}

export interface VerificationResult {
  decision_status: ReconciliationStatus;
  passed: boolean;
  challenges: string[];
  checks: Array<{ check: string; passed: boolean; detail: string }>;
}

export interface InvariantResult {
  rule_id: string;
  status: "PASSED" | "FAILED" | "NOT_APPLICABLE";
  expected?: string | null;
  actual?: string | null;
  difference?: string | null;
  evidence_ids: string[];
  reason: string;
  severity: string;
}

export interface ControllerDecision {
  case_id: string;
  payment_id: string;
  status: ReconciliationStatus;
  confidence_score: number;
  confidence_band: ConfidenceBand;
  financial_impact: string;
  expected_settlement?: string | null;
  actual_settlement?: string | null;
  expected_fee?: string | null;
  refund_total: string;
  difference?: string | null;
  reason_codes: string[];
  evidence_ids: string[];
  supporting_evidence: string[];
  contradicting_evidence: string[];
  confidence_factors: Record<string, number>;
  risk_score: number;
  risk_factors: string[];
  invariants: InvariantResult[];
  ai_investigation?: AIInvestigationResult | null;
  verification?: VerificationResult | null;
}

export interface ReconciliationCase {
  case_id: string;
  run_id: string;
  payment_id: string;
  order_id?: string | null;
  merchant_id: string;
  status: ReconciliationStatus;
  decision: ControllerDecision;
  graph: EvidenceGraph;
  evidence: EvidenceItem[];
  tool_calls: AgentToolCall[];
  invariants: InvariantResult[];
  ai_investigation?: AIInvestigationResult | null;
  risk_score: number;
  risk_factors: string[];
  investigation_timeline: string[];
  created_at: string;
}

export interface ControllerRun {
  run_id: string;
  dataset_id: string;
  started_at: string;
  finished_at: string;
  duration_ms: number;
  metrics: RunMetrics;
  cases: ReconciliationCase[];
  audit_events: AuditEvent[];
}

export interface FailureRecord {
  case_id: string;
  payment_id: string;
  expected: ReconciliationStatus;
  predicted: ReconciliationStatus;
  root_cause: string;
  evidence_available: string[];
  failure_category: string;
  financial_impact: string;
}

export interface EvaluationRun {
  evaluation_run_id: string;
  controller_run_id: string;
  dataset_id: string;
  created_at: string;
  metrics: EvaluationMetrics;
  failures: FailureRecord[];
}

export interface AuditEvent {
  event_id: string;
  timestamp: string;
  actor: string;
  action: string;
  entity: string;
  entity_id: string;
  inputs_ref: Record<string, unknown>;
  output_ref: Record<string, unknown>;
  reason: string;
  correlation_id: string;
}

export interface ComparisonRow {
  mode: "deterministic_only" | "ai_assisted";
  controller_run_id: string;
  evaluation_run_id: string;
  metrics: EvaluationMetrics;
  controller_metrics: RunMetrics;
  failures: number;
}

export interface ControllerComparison {
  dataset_id: string;
  comparison: ComparisonRow[];
}

export interface AuditWorldResult {
  world: WorldBuildResult;
  controller_run: ControllerRun;
  evaluation: EvaluationRun;
  comparison: ControllerComparison;
  survival_status: string;
}

export type PageId =
  | "home"
  | "worlds"
  | "audits"
  | "review"
  | "insights"
  | "settings"
  | "world-builder"
  | "world-explorer"
  | "reconciliation"
  | "investigations"
  | "evidence-graph"
  | "human-review"
  | "evaluation-lab"
  | "controller-runs"
  | "audit-trail";

export type PrimaryPageId = "home" | "worlds" | "audits" | "review" | "insights" | "settings";
