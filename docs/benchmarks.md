# Benchmarks

Date: 2026-08-25

Benchmarks are measured from local artifacts and should not be edited after a run.

## Commands

```powershell
python scripts/world_demo.py --seed 42
python scripts/ai_value_benchmark.py --records 1000 --seed 42
python scripts/phase_c_heldout.py --records-per-slice 200 --seed 42000
python scripts/phase_c_benchmark.py --counts 100 500 1000 5000 10000 50000 --mode MIXED --seed 42 --output phase_c_benchmark.json
python scripts/phase_c_concurrency.py --levels 1 5 10 25 50 --records 120 --seed 9000
python scripts/phase_c_demo_reliability.py --runs 10 --seed 42 --records 500
```

## Frozen Demo

Artifact: `data/world_demo/latest_world_summary.json`

- World ID: `FW_0a7d61b20d15`
- Dataset ID: `WORLD_FW_0a7d61b20d15`
- Seed: `42`
- Orders: 500
- Payments: 506
- Settlements: 486
- Refunds: 60
- Controlled anomalies: 112
- Payment volume: INR 2148789.81
- LLM calls: 0 by default
- Estimated AI cost: USD 0.00 by default

## AI-Assisted Demo Metrics

| Metric | Value |
| --- | ---: |
| Accuracy | 0.9960 |
| Precision | 0.9868 |
| Recall | 0.9953 |
| F1 | 0.9907 |
| Auto-resolution | 0.9921 |
| Human escalation | 0.0079 |
| Unresolved | 0.0000 |
| Throughput | 647.36 records/sec |
| P50 latency | 0.9167 ms |
| P95 latency | 2.1279 ms |
| P99 latency | 3.2324 ms |
| Financial error impact | INR 647.36 |

## AI Vs Baseline, Frozen Demo

| Metric | Baseline | Auditra AI |
| --- | ---: | ---: |
| Accuracy | 0.9704 | 0.9960 |
| Precision | 0.8913 | 0.9868 |
| Recall | 0.9646 | 0.9953 |
| F1 | 0.8951 | 0.9907 |
| Auto-resolution | 0.9664 | 0.9921 |
| Human review | 0.0336 | 0.0079 |
| P95 latency | 1.8545 ms | 2.1279 ms |
| Cost / 1K | USD 0.00 | USD 0.00 |
| Failures | 15 | 2 |

## Held-Out Benchmark

Artifact: `evaluation/phase_c_heldout.json`

| Mode | Records | Weighted accuracy | Weighted F1 | Failures | Error impact | Incorrect amount |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 1221 | 0.9771 | 0.9503 | 28 | INR 24665.77 | INR 105728.82 |
| ai_assisted | 1221 | 0.9992 | 0.9985 | 1 | INR 242.03 | INR 742.18 |

## Scale Benchmark

Artifact: `evaluation/phase_c_benchmark.json`

| Records | Mode | Status | Throughput r/s | Accuracy | F1 | Failures |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 100 | deterministic_only | completed | 138.79 | 0.9600 | 0.8867 | 4 |
| 100 | ai_assisted | completed | 123.99 | 0.9600 | 0.8867 | 4 |
| 500 | deterministic_only | completed | 146.85 | 0.9480 | 0.8925 | 26 |
| 500 | ai_assisted | completed | 86.83 | 0.9480 | 0.8925 | 26 |
| 1000 | deterministic_only | completed | 129.96 | 0.9790 | 0.8439 | 21 |
| 1000 | ai_assisted | completed | 125.57 | 0.9790 | 0.8439 | 21 |
| 5000 | deterministic_only | completed | 144.42 | 0.9636 | 0.8053 | 182 |
| 5000 | ai_assisted | completed | 120.66 | 0.9636 | 0.8053 | 182 |
| 10000 | deterministic_only | completed | 143.29 | 0.9655 | 0.8122 | 345 |
| 10000 | ai_assisted | completed | 118.04 | 0.9656 | 0.8122 | 344 |
| 50000 | not_run | rejected_by_input_contract | - | - | - | - |

## Demo Reliability

Artifact: `evaluation/phase_c_demo_reliability.json`

The final demo completed 10 of 10 runs with zero system failures. Average duration was 908.88 ms. Every run produced 506 records, 0.9960 accuracy, 0.9907 F1, and 2 evaluation failures.
