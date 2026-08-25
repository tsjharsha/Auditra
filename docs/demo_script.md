# Five-Minute Demo Script

## 0:00-0:20

Open Auditra at `http://127.0.0.1:5173`.

Say:

```text
Most financial AI demos start with a dataset. Auditra starts one step earlier.
```

## 0:20-0:45

Use:

```text
Generate an Indian e-commerce merchant with 500 orders, UPI and card payments, 2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies.
```

Click `Build Financial World`.

## 0:45-1:10

Show understanding, schema, relationship model, rules, validation, and world summary.

Measured seed-42 demo:

- 500 orders
- 506 payments
- 486 settlements
- 60 refunds
- 112 controlled anomalies
- INR 2145335.29 payment volume

## 1:10-2:00

Click `Audit This World`.

Show controller metrics:

- 99.60% accuracy
- 99.21% automatic resolution
- 0.79% human escalation
- 629.88 records/sec in AI-assisted mode in the latest acceptance run
- 0 external LLM calls by default

## 2:00-3:00

Open a difficult transaction in Investigations.

Show:

- financial discrepancy
- hypotheses
- tool activity
- evidence graph
- verification checks
- final decision

## 3:00-3:30

Open Human Review.

Show a case where Auditra escalates instead of pretending certainty.

## 3:30-4:30

Open Evaluation Lab and show Break The Controller results.

Seed-42 world demo result:

- controller failed 2 cases
- failure taxonomy: classification error
- incorrectly classified amount: INR 3090.57
- financial error impact: INR 647.36

## 4:30-5:00

Show AI vs deterministic baseline.

For the measured seed-42 world demo, AI reduced failures from 15 to 2 by resolving refund-mismatch over-escalation only when deterministic invariant verification passed. Conflicting evidence still stays in human review.
