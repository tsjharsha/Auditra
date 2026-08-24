# Benchmarks

Benchmarks are measured, not hardcoded.

## Commands

```powershell
python scripts/world_demo.py --seed 42
python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42
```

## World Demo, Seed 42

- Orders: 500
- Payments: 506
- Settlements: 486
- Refunds: 60
- Controlled anomalies: 112
- Payment volume: INR 2145335.29
- Accuracy: 0.9585
- Precision: 0.8067
- Recall: 0.9011
- F1: 0.8199
- Automatic resolution: 0.9664
- Human escalation: 0.0336
- AI-assisted throughput: 813.47 records/sec
- AI-assisted P95 latency: 1.723 ms
- LLM calls: 0 by default
- Agent tool calls: 6462
- Estimated AI cost: USD 0.00 by default

## AI vs Baseline, Same World

| Mode | Accuracy | F1 | Auto Resolution | Throughput | Tool Calls | Failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 0.9585 | 0.8199 | 0.9664 | 1078.87/sec | 5020 | 21 |
| ai_assisted | 0.9585 | 0.8199 | 0.9664 | 813.47/sec | 6462 | 21 |

AI-assisted mode improved evidence depth and investigation traceability in this run, not classification accuracy. Auditra reports that without inflating the result.

## Synthetic Benchmark, MIXED Seed 42

| Records | Throughput | P95 Latency | Accuracy | Failures | AI Investigations |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 1092.68/sec | 1.7592 ms | 0.9600 | 4 | 27 |
| 500 | 794.09/sec | 2.3327 ms | 0.9480 | 26 | 132 |
| 1000 | 636.98/sec | 2.5751 ms | 0.9790 | 21 | 246 |
