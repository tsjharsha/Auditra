# Auditra

From financial intent to verified control.

Auditra is an autonomous financial control system. A user describes a financial world in natural language; Auditra builds a deterministic synthetic finance environment, stresses it with controlled anomalies, audits it with deterministic controls and bounded AI investigation, then independently proves what the controller got right and wrong.

It is not a chatbot, and it does not ask an LLM to do authoritative money math.

## Product Loop

```text
CREATE -> STRESS -> AUDIT -> PROVE
```

1. Describe a financial system.
2. Preview schema and relationships.
3. Generate a validated financial world.
4. Inject hidden controlled anomalies.
5. Run reconciliation and AI-assisted investigation.
6. Inspect evidence, graph, hypotheses, verification, and human review.
7. Compare AI-assisted control with deterministic baseline.

## What Works

- Prompt-to-`FinancialWorldSpec` world builder.
- Deterministic generation of merchants, orders, payments, settlements, refunds, and fee rules.
- Schema preview and relationship model.
- World validation before audit.
- Hidden ground truth isolated from the controller.
- CSV, JSON, and Razorpay test-data adapters.
- Decimal-only financial arithmetic.
- Financial invariant engine.
- Evidence graph with source records, investigation, decision, and evidence nodes.
- Bounded AI investigation with hypotheses, self-challenge, typed tools, and verification.
- Human review actions.
- Independent evaluation with confusion matrix, failure taxonomy, financial impact, latency, throughput, tool calls, LLM calls, and estimated cost.
- Optional OpenAI providers for world understanding and investigation planning.
- Optional PostgreSQL persistence via `AUDITRA_DATABASE_URL`.

## Quick Start

Use Python 3.11+.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Run the API:

```powershell
$env:PYTHONPATH="$PWD\backend"
uvicorn auditra.api:app --reload --host 127.0.0.1 --port 8000
```

Open the app:

```text
http://127.0.0.1:5173/
```

If you only need the static file:

```text
frontend/index.html
```

Run the final product demo from CLI:

```powershell
python scripts/world_demo.py --seed 42
```

Run benchmarks:

```powershell
python scripts/benchmark.py --counts 100 500 1000 --mode MIXED --seed 42
```

## Measured Seed-42 World Demo

Prompt:

```text
Generate an Indian e-commerce merchant with 500 orders, UPI and card payments, 2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies.
```

Result:

- 500 orders
- 506 payments
- 486 settlements
- 60 refunds
- 112 controlled anomalies
- INR 2145335.29 payment volume
- 95.85% accuracy
- 96.64% automatic resolution
- 3.36% human escalation
- 813.47 records/sec AI-assisted throughput in the latest acceptance run
- 0 external LLM calls by default

AI-assisted mode added evidence depth and investigation traceability in this run. It did not improve classification accuracy versus deterministic baseline, and Auditra reports that honestly.

## API Surface

- `POST /worlds/preview`
- `POST /worlds/build`
- `POST /worlds/spec`
- `GET /worlds`
- `GET /worlds/{world_id}`
- `POST /worlds/{world_id}/audit`
- `POST /ingest/{adapter}`
- `POST /datasets`
- `GET /datasets`
- `POST /controller/runs`
- `GET /controller/runs/{id}`
- `GET /reconciliation`
- `GET /reconciliation/{id}`
- `GET /exceptions`
- `GET /exceptions/{id}`
- `GET /evidence/{id}`
- `GET /graph/{transaction_id}`
- `POST /investigations/{id}/run`
- `POST /review/{id}`
- `GET /audit`
- `POST /evaluation/runs`
- `POST /evaluation/compare`
- `GET /evaluation/runs/{id}`
- `GET /evaluation/runs/{id}/failures`
- `POST /demo`

## Optional LLM Providers

Local demos are offline by default. To use OpenAI for structured world understanding or investigation planning:

```powershell
$env:OPENAI_API_KEY="..."
$env:AUDITRA_USE_OPENAI_WORLD_BUILDER="1"
$env:AUDITRA_USE_OPENAI_INVESTIGATOR="1"
$env:AUDITRA_OPENAI_MODEL="gpt-5-mini"
```

LLMs produce structured specs or investigation plans only. Deterministic systems generate records, compute money, verify decisions, and evaluate results.

## Optional PostgreSQL

Apply:

```text
migrations/001_initial_postgres.sql
```

Then set:

```powershell
$env:AUDITRA_DATABASE_URL="postgresql://..."
```

Without a database URL, Auditra uses in-memory storage for the local demo.

## Documentation

- [Final Architecture](docs/final_architecture.md)
- [World Builder](docs/world_builder.md)
- [Agent Design](docs/agent_design.md)
- [Data Model](docs/data_model.md)
- [Evaluation](docs/evaluation.md)
- [Benchmarks](docs/benchmarks.md)
- [Security](docs/security.md)
- [Demo Script](docs/demo_script.md)
- [Galarix Integration Boundary](docs/galarix_integration.md)
- [Engineering Decisions](docs/decisions.md)
- [Final Quality Report](docs/final_quality_report.md)
