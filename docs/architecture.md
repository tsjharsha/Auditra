# Auditra Architecture

Auditra is a bounded AI finance controller for multi-source payment reconciliation. The first implementation is a modular monolith with deterministic finance logic, a bounded investigation tool layer, verification, human-review states, and independent evaluation.

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
find_payment | find_order | find_settlement | find_refunds | compare_amounts
        |
        v
Deterministic reconciliation engine
Decimal arithmetic | fee calculation | duplicate checks | timing windows
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
6. A verification pass challenges every decision before final status is emitted.
7. Evaluation compares controller output with hidden ground truth after the run.

## Agent Loop

The current investigation agent is deterministic and tool-using. It is intentionally bounded:

```text
INVESTIGATE
  locate payment
  locate order
  locate settlement
  locate refunds
  locate fee rule
  inspect related records
DECIDE
  classify by deterministic rules
CHALLENGE
  ask what would make the decision wrong
VERIFY
  run counterfactual checks
RESOLVE / ESCALATE
```

LLM availability is not required. Future LLM use should be limited to explanation, hypothesis generation, and exception summarization. It must not perform authoritative arithmetic or mutate source records.

## Evidence Graph

Each reconciliation case creates graph nodes for:

- merchant
- customer
- order
- payment
- settlement
- refund
- fee rule

Edges capture relationships such as `creates`, `settles_through`, `adjusted_by`, `governed_by`, `receives`, and `pays`. Every important node/edge has an evidence id that points back to a source record or rule.

## Evaluation Architecture

Evaluation is separate from controller execution:

```text
Scenario generator
  visible records ---------------------> controller
  hidden ground truth -> evaluator <---- controller output
```

The controller never sees scenario labels, expected statuses, failure metadata, or evaluator outputs. Metrics are computed across the entire batch.

## Trust Boundaries

- Source records are immutable Pydantic models during a run.
- Ground truth is hidden from controller endpoints.
- Tool calls are allowlisted and logged.
- No tool can initiate payments, refunds, payouts, or database mutation.
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

Malformed uploads and persistent database storage are planned for the next implementation phase. The first slice uses generated/API-shaped records and in-memory storage so the demo has no manual database setup.

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
