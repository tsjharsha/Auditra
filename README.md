# Auditra

Autonomous financial control you can verify.

Auditra is an AI Finance Controller focused on one strong finance-ops loop: multi-source payment reconciliation across orders, payments, settlements, refunds, and fee rules. The controller uses deterministic financial arithmetic, bounded investigation tools, evidence graphs, verification checks, human escalation, and independent evaluation.

It is not a chatbot and it does not ask an LLM to do authoritative money math.

## What Works Now

- Deterministic scenario generation for 10 to 10,000 payment-level records.
- Linked orders, payments, settlements, refunds, merchants, and fee rules.
- Hidden ground truth isolated from controller execution.
- Decimal-only fee, refund, settlement, difference, and impact calculations.
- Bounded tool layer with structured tool-call logs.
- Evidence graph per transaction.
- Verification stage before final decision.
- Human-review and unresolved states.
- Independent evaluator with accuracy, precision, recall, F1, false-positive and false-negative rates, throughput, latency, and financial impact metrics.
- FastAPI endpoints for datasets, controller runs, reconciliation cases, exceptions, evidence, graphs, audit trail, evaluation, and demo mode.

## Quick Start

Use Python 3.11+.

```powershell
python -m pip install -r requirements.txt
python scripts/demo_run.py --mode MIXED --records 1000 --seed 42
```

The demo writes source CSVs plus `controller_run.json`, `evaluation_report.json`, and `latest_summary.json` under `data/demo/`.

Run tests:

```powershell
python -m unittest discover -s tests -v
```

Run the API:

```powershell
$env:PYTHONPATH="$PWD\backend"
uvicorn auditra.api:app --reload --host 127.0.0.1 --port 8000
```

Open API docs at:

```text
http://127.0.0.1:8000/docs
```

Open the local console:

```text
frontend/index.html
```

## Demo Flow

1. Create a 1,000-record scenario.
2. Run the controller.
3. Inspect metrics from actual execution.
4. Open a resolved case and inspect the evidence graph.
5. Open a review/escalated case and inspect why it was not auto-resolved.
6. Run evaluation and reveal hidden ground truth.
7. Inspect every failure record.

CLI:

```powershell
python scripts/demo_run.py --mode ADVERSARIAL --records 1000 --seed 42
```

API:

```powershell
curl -X POST http://127.0.0.1:8000/demo -H "Content-Type: application/json" -d "{\"mode\":\"ADVERSARIAL\",\"record_count\":1000,\"seed\":42}"
```

The response says either `CONTROLLER SURVIVED` or `CONTROLLER FAILED N CASES` based on measured evaluation output.

## API Surface

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
- `POST /evaluation/scenarios`
- `POST /evaluation/runs`
- `GET /evaluation/runs/{id}`
- `GET /evaluation/runs/{id}/failures`
- `POST /demo`

## Architecture

See [docs/architecture.md](docs/architecture.md).

The implementation separates:

- deterministic finance engine
- bounded investigation tools
- verification layer
- human escalation
- independent evaluation

## Galarix Reference

Galarix was inspected for selective reuse ideas only. Auditra does not copy the Galarix product, UI, routes, branding, or synthetic-data pipeline.

See [docs/galarix_reuse_map.md](docs/galarix_reuse_map.md).

## Current Limitations

- Persistence is in-memory for the first working slice.
- Upload ingestion is not yet exposed through file upload endpoints.
- The frontend is a lightweight static console in this phase.
- LLM explanation is intentionally disabled by default.
- Razorpay test-mode adapters are planned but not required for the local demo.
