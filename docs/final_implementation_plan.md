# Final Implementation Plan

This plan is now the implementation record for the final productization pass.

## Completed P0

- Financial World Builder module with typed `FinancialWorldSpec`.
- Natural-language prompt parsing with deterministic offline path and opt-in provider path; Groq is the primary real-model submission provider.
- Schema preview for MERCHANT, ORDER, PAYMENT, SETTLEMENT, REFUND, and FEE_RULE.
- Relationship model preview.
- Deterministic world generation from prompt plus seed.
- World validation before exposure.
- Controlled anomaly injection with hidden ground truth.
- World summary with actual financial amounts.
- Audit pipeline over generated worlds.
- Typed AI investigation tools, hypotheses, self-challenge, verification, evidence IDs, and confidence factors.
- Financial invariant engine.
- Evidence graph with investigation, decision, evidence, and source record nodes.
- Human review actions recorded through the store and optional PostgreSQL.
- Independent evaluation and AI-vs-baseline comparison.
- CSV, JSON, and Razorpay test-data adapters.
- Polished dependency-free frontend flow.
- PostgreSQL migration and optional persistence repository.

## Intentionally Deferred

- Live Razorpay API calls. The adapter is test-data only and performs no money movement.
- Mandatory external LLM use. Real providers are opt-in because local demos must not require secrets.
- Full React/Vite migration. The current frontend is dependency-free so the existing localhost demo remains stable.
- Authentication and role-based access.
- Large-scale 50,000-record benchmark, pending database-backed execution environment.

## Acceptance Commands

```powershell
python -m unittest discover -s tests -v
py -3.13 -m unittest discover -s tests -p test_api.py -v
python scripts/world_demo.py --seed 42
python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42
```
