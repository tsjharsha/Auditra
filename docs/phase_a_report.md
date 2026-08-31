# Phase A Report

Date: 2026-08-25

## Scope

Phase A made the AI layer real, measurable and fail-closed without giving it authority over money movement. LLMs can produce structured world specs and investigation plans; deterministic code still generates records, runs arithmetic, verifies decisions and evaluates results.

## Implementation Summary

- Added shared `LLMProvider` abstractions with external, mock and offline providers; current submission evidence uses Groq through that interface.
- Added env-configured model, temperature, max tokens, timeout, retry count and token-cost fields.
- Replaced direct world-builder model calls with typed structured-output validation and malformed-output retry behavior.
- Added strict `FinancialWorldSpec` validation for currencies, payment methods, anomaly names and rates.
- Changed the AI investigator to execute provider-selected typed tool plans through a bounded allowlist.
- Added fail-closed `ai_unavailable` results that escalate to `HUMAN_REVIEW` instead of fabricating offline hypotheses.
- Hardened tools with input validation, max calls, timeout accounting, result-size truncation and failure logging.
- Removed hidden anomaly labels from controller-visible generated records.
- Added class-level precision, recall and F1 to evaluator output.
- Added `scripts/ai_value_benchmark.py`.

## Verification

```powershell
python -m unittest discover -s tests -v
py -3.13 -m unittest discover -s tests -p test_api.py -v
python scripts/ai_value_benchmark.py --records 1000 --seed 42
python scripts/compare_controllers.py --records 1000 --mode MIXED --seed 42
python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42
python scripts/world_demo.py --seed 42
```

- Default Python: 24 tests run, 22 passed, 2 skipped because FastAPI is not installed in that interpreter.
- Python 3.13 API tests: 2 passed.

## AI Value Benchmark

Command:

```powershell
python scripts/ai_value_benchmark.py --records 1000 --seed 42
```

Dataset:

- World: `FW_3be92154f491`
- Payments: 1022
- Controlled anomalies: 220
- Payment volume: INR 4285730.54

| Mode | Accuracy | Precision | Recall | F1 | Failures | Escalation | AI Invocation | P95 Latency | Tool Calls | LLM Calls | Cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| deterministic_only | 0.9726 | 0.9105 | 0.9615 | 0.9134 | 28 | 0.0382 | 0.0000 | 1.2069 ms | 10118 | 0 | USD 0.00 |
| ai_assisted | 0.9971 | 0.9906 | 0.9959 | 0.9930 | 3 | 0.0137 | 0.2153 | 1.9602 ms | 12606 | 0 | USD 0.00 |

Measured lift:

- Accuracy: +0.0245
- F1: +0.0796
- Failures reduced: 25 of 28
- Failure-rate reduction: 0.8929
- Escalation-rate reduction: 0.0245
- Incorrectly classified amount reduction: INR 94970.97
- Financial error impact reduction: INR 16084.52
- P95 latency increase: +0.7533 ms

Class-level lift:

| Class | Baseline Recall | AI Recall | Recall Lift | Baseline F1 | AI F1 | F1 Lift |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AMOUNT_MISMATCH | 0.6923 | 0.9670 | +0.2747 | 0.8182 | 0.9832 | +0.1650 |
| HUMAN_REVIEW | 1.0000 | 1.0000 | +0.0000 | 0.5283 | 1.0000 | +0.4717 |
| DUPLICATE | 1.0000 | 1.0000 | +0.0000 | 1.0000 | 1.0000 | +0.0000 |
| MISSING_SETTLEMENT | 1.0000 | 1.0000 | +0.0000 | 1.0000 | 1.0000 | +0.0000 |
| PARTIAL_MATCH | 1.0000 | 1.0000 | +0.0000 | 0.9610 | 0.9610 | +0.0000 |
| REFUND_ADJUSTED | 1.0000 | 1.0000 | +0.0000 | 1.0000 | 1.0000 | +0.0000 |
| TIMING_MISMATCH | 1.0000 | 1.0000 | +0.0000 | 1.0000 | 1.0000 | +0.0000 |

## Interpretation

The lift comes from refund-mismatch over-escalations. The AI planner selects refund/fee/partial-settlement hypotheses and supporting tools; the controller then verifies that only `SETTLEMENT_NET_AMOUNT` failed and that `AMOUNT_MISMATCH` deterministic verification passes. Conflicting-evidence cases still remain `HUMAN_REVIEW` because merchant-consistency invariants fail.

The standard `ScenarioGenerator` mixed benchmark still shows no classification lift because it does not exercise the same prompt-world refund-conflict pattern. That is intentional: Phase A reports AI value only where the measured dataset proves it.

## Safety Notes

- LLM failures produce `ai_unavailable=True` and `HUMAN_REVIEW`.
- Malformed structured output retries once and then fails closed.
- Tool calls are allowlisted, typed through mapped call paths, input-validated, logged and capped.
- Public/controller-visible payload tests assert no `ground_truth`, `expected_status`, hidden `scenario`, or visible `"anomaly":` labels.
- Default local runs can use the offline provider; real Groq evidence requires explicit environment configuration and `GROQ_API_KEY`.
