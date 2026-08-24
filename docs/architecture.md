# Auditra Architecture

Auditra is a bounded AI finance controller for multi-source payment reconciliation. The implementation is a modular monolith with deterministic finance logic, a bounded investigation tool layer, financial invariants, an AI-assisted hypothesis layer, verification, human-review states, and independent evaluation.

## System Architecture

```text
CSV/API-shaped records
        |
        v
Typed ingestion models
Order | Payment | Settlement | Refund | FeeRule | Merchant
        |
        v
Dataset index + evidence store
        |
        v
Bounded investigation tools
find_payment | find_order | find_merchant | find_settlement | find_refunds
compare_amounts | check_duplicate | get_graph_neighborhood | verify_hypothesis
        |
        v
Deterministic reconciliation engine
Decimal arithmetic | fee calculation | duplicate checks | timing windows
        |
        v
Financial invariant engine
rule_id -> passed / failed / not_applicable -> evidence IDs
        |
        v
AI-assisted hypothesis layer
dynamic tools | hypotheses | self-challenge | evidence-linked recommendation
        |
        v
Verification layer
challenge decision -> verify counterfactuals -> resolve or escalate
        |
        v
Controller run
cases | decisions | evidence graph | tool calls | audit events | metrics
        |
        v
Independent evaluator
hidden ground truth -> metrics -> failures -> break-the-controller report
```

## Data Flow

1. Scenario generation creates coherent linked records for merchants, orders, payments, settlements, refunds, and fee rules.
2. Hidden ground truth is stored on `DatasetBundle.ground_truth`; controller APIs do not expose it.
3. The controller builds indexes over source records and reconciles every payment.
4. Each investigation uses allowlisted tools with a tool-call budget.
5. Financial arithmetic uses `Decimal` and deterministic code.
6. Financial invariants emit rule-level pass/fail/not-applicable outputs.
7. Exception and low-confidence cases run the AI-assisted hypothesis layer.
8. A verification pass challenges every decision before final status is emitted.
9. Evaluation compares controller output with hidden ground truth after the run.

## Agent Loop

The base investigation is deterministic and tool-using. Exception and low-confidence cases then run an AI-assisted hypothesis layer that is intentionally bounded:

```text
INVESTIGATE
  locate payment
  locate order
  locate settlement
  locate refunds
  locate fee rule
  inspect related records
  evaluate financial invariants
HYPOTHESIZE
  propose candidate explanations
  choose tools based on case shape
  attach supporting and contradicting evidence IDs
DECIDE
  classify by deterministic rules
CHALLENGE
  ask what would make the decision wrong
VERIFY
  run counterfactual checks
RESOLVE / ESCALATE
```

LLM availability is not required. The default provider is offline and structured. Future LLM use should be limited to explanation, hypothesis generation, and exception summarization. It must not perform authoritative arithmetic or mutate source records.

## Evidence Graph

Each reconciliation case creates graph nodes for:

- transaction
- investigation
- decision
- evidence
- merchant
- customer
- order
- payment
- settlement
- refund
- fee rule

Edges capture relationships such as `CREATED`, `PAID`, `SETTLED`, `REFUNDED`, `GOVERNED_BY`, `BELONGS_TO`, `RELATED_TO`, `SUPPORTED_BY`, `CONTRADICTED_BY`, `INVESTIGATED_BY`, and `RESULTED_IN`. Edges carry confidence, evidence IDs, source-system metadata, and timestamps where source records provide them.

## Evaluation Architecture

Evaluation is separate from controller execution:

```text
Scenario generator
  visible records ---------------------> controller
  hidden ground truth -> evaluator <---- controller output
```

The controller never sees scenario labels, expected statuses, failure metadata, or evaluator outputs. `DatasetIndex` strips `ground_truth` before any tool receives data. Metrics are computed across the entire batch.

## Trust Boundaries

- Source records are immutable Pydantic models during a run.
- Ground truth is hidden from controller endpoints.
- Tool calls are allowlisted and logged.
- No tool can initiate payments, refunds, payouts, or database mutation.
- AI output is explanatory and cannot override deterministic arithmetic.
- Human review is an explicit state, not a failure of the app.

## Failure Handling

Auditra escalates or marks unresolved when:

- fee rules are missing
- source records conflict
- confidence is too low
- verification fails
- duplicate and missing-settlement explanations compete
- evidence cannot establish a relationship
- the tool budget is exhausted

Malformed uploads and persistent database storage are planned for the next implementation phase. The current slice uses generated/API-shaped records and in-memory storage so the demo has no manual database setup.

## Database Target Schema

The production persistence layer should use tables equivalent to:

- `merchants`
- `orders`
- `payments`
- `settlements`
- `refunds`
- `fee_rules`
- `transaction_links`
- `reconciliation_cases`
- `evidence_items`
- `agent_runs`
- `agent_tool_calls`
- `controller_decisions`
- `audit_events`
- `evaluation_runs`
- `evaluation_cases`
- `ground_truth_cases`

Important indexes:

- `payment_id`
- `order_id`
- `settlement_id`
- `merchant_id`
- `timestamp`
- `status`
- `run_id`

## Security Considerations

- Never commit live Razorpay, LLM, database, or payout credentials.
- Use test-mode provider adapters only.
- Keep API keys in environment variables.
- Validate uploads before ingestion.
- Prevent path traversal on uploaded files.
- Limit file size and quarantine malformed records.
- Do not expose hidden ground truth from controller routes.
