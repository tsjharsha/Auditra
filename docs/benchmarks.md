# Benchmarks

Benchmarks are measured, not hardcoded.

## Commands

```powershell
python scripts/world_demo.py --seed 42
python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42
python scripts/ai_value_benchmark.py --records 1000 --seed 42
```

## World Demo, Seed 42

- Orders: 500
- Payments: 506
- Settlements: 486
- Refunds: 60
- Controlled anomalies: 112
- Payment volume: INR 2145335.29
- Accuracy: 0.9960
- Precision: 0.9868
- Recall: 0.9953
- F1: 0.9907
- Automatic resolution: 0.9921
- Human escalation: 0.0079
- AI-assisted throughput: 629.88 records/sec
- AI-assisted P95 latency: 2.2599 ms
- LLM calls: 0 by default
- Agent tool calls: 6276
- Estimated AI cost: USD 0.00 by default

## AI vs Baseline, Same World

| Mode | Accuracy | F1 | Auto Resolution | Human Review | Throughput | Tool Calls | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 0.9704 | 0.8951 | 0.9664 | 0.0336 | 994.01/sec | 5020 | 15 |
| ai_assisted | 0.9960 | 0.9907 | 0.9921 | 0.0079 | 629.88/sec | 6276 | 2 |

AI-assisted mode reduced refund-mismatch over-escalation after deterministic invariant verification. It did not change conflicting-evidence cases that failed merchant-consistency controls.

## Phase A AI-Value Benchmark

Command:

```powershell
python scripts/ai_value_benchmark.py --records 1000 --seed 42
```

| Mode | Accuracy | F1 | Failures | Escalation | AI Invocation | P95 Latency | Tool Calls | LLM Calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 0.9726 | 0.9134 | 28 | 0.0382 | 0.0000 | 1.2069 ms | 10118 | 0 |
| ai_assisted | 0.9971 | 0.9930 | 3 | 0.0137 | 0.2153 | 1.9602 ms | 12606 | 0 |

Key lift:

- Accuracy: +0.0245
- F1: +0.0796
- AMOUNT_MISMATCH recall: 0.6923 -> 0.9670
- Failures reduced: 25
- Financial error impact reduced by INR 16084.52

## Synthetic Benchmark, MIXED Seed 42

| Records | Throughput | P95 Latency | Accuracy | Failures | AI Investigations |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 876.42/sec | 1.9466 ms | 0.9600 | 4 | 27 |
| 500 | 863.80/sec | 1.8671 ms | 0.9480 | 26 | 132 |
| 1000 | 615.51/sec | 2.1989 ms | 0.9790 | 21 | 246 |
