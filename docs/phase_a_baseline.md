# Phase A Baseline

Date: 2026-08-25

## Commands

```powershell
python -m unittest discover -s tests -v
python scripts/world_demo.py --seed 42
python scripts/compare_controllers.py --records 1000 --mode MIXED --seed 42
```

## Test Baseline

- Default Python: 16 tests discovered, 14 passed, 2 skipped because FastAPI is not installed in that interpreter.

## Prompt World Demo Baseline

Prompt:

```text
Generate an Indian e-commerce merchant with 500 orders, UPI and card payments, 2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies.
```

World:

- Orders: 500
- Payments: 506
- Settlements: 486
- Refunds: 60
- Controlled anomalies: 112
- Payment volume: INR 2145335.29

AI-assisted controller baseline:

- Accuracy: 0.9585
- Precision: 0.8067
- Recall: 0.9011
- F1: 0.8199
- Auto-resolution: 0.9664
- Human escalation: 0.0336
- Throughput: 562.6 records/sec
- Median latency: 0.9775 ms
- P95 latency: 2.3105 ms
- P99 latency: 3.7548 ms
- Tool calls: 6462
- LLM calls: 0
- Estimated AI cost: USD 0.00
- Failure count: 21
- Failure taxonomy: OVER_ESCALATION 13, CLASSIFICATION_ERROR 5, FALSE_EXCEPTION 3

Same-world comparison:

| Mode | Accuracy | Precision | Recall | F1 | Auto-Resolution | Human Escalation | Throughput | P95 Latency | Tool Calls | LLM Calls | Cost | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 0.9585 | 0.8067 | 0.9011 | 0.8199 | 0.9664 | 0.0336 | 856.03/sec | 1.8355 ms | 5020 | 0 | USD 0.00 | 21 |
| ai_assisted | 0.9585 | 0.8067 | 0.9011 | 0.8199 | 0.9664 | 0.0336 | 562.6/sec | 2.3105 ms | 6462 | 0 | USD 0.00 | 21 |

## MIXED 1,000-Record Baseline

| Mode | Accuracy | Precision | Recall | F1 | Throughput | P95 Latency | Tool Calls | LLM Calls | Cost | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 0.9790 | 0.8387 | 0.8515 | 0.8439 | 879.44/sec | 1.5565 ms | 9838 | 0 | USD 0.00 | 21 |
| ai_assisted | 0.9790 | 0.8387 | 0.8515 | 0.8439 | 749.03/sec | 2.6631 ms | 12650 | 0 | USD 0.00 | 21 |

## Baseline Observations

- The local AI-assisted mode is still using offline structured planning by default.
- AI investigation adds hypotheses, evidence links, and tool traces but does not improve classification accuracy in the baseline.
- The prompt-generated world baseline shows over-escalation on refund-mismatch cases and duplicate timing ambiguity.
- Phase A should measure class-level lift and avoid claiming global improvement unless the evaluation proves it.
