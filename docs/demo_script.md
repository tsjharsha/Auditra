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

- 95.85% accuracy
- 96.64% automatic resolution
- 3.36% human escalation
- 813.47 records/sec in AI-assisted mode in the latest acceptance run
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

- controller failed 21 cases
- failure taxonomy: over-escalation, classification error, false exception
- incorrectly classified amount: INR 80036.10
- financial error impact: INR 39687.93

## 4:30-5:00

Show AI vs deterministic baseline.

For the measured seed-42 world demo, AI added richer investigation evidence but did not improve accuracy. The UI shows that honestly.
