# Auditra

Autonomous financial control you can verify.

Auditra is an AI Finance Controller focused on one strong finance-ops loop: multi-source payment reconciliation across orders, payments, settlements, refunds, and fee rules. The controller uses deterministic financial arithmetic, bounded investigation tools, financial invariants, dynamic AI-assisted hypotheses, evidence graphs, verification checks, human escalation, and independent evaluation.

It is not a chatbot and it does not ask an LLM to do authoritative money math.

## What Works Now

- Deterministic scenario generation for 10 to 10,000 payment-level records.
- Linked orders, payments, settlements, refunds, merchants, and fee rules.
- Hidden ground truth isolated from controller execution.
- Decimal-only fee, refund, settlement, difference, and impact calculations.
- Bounded tool layer with structured tool-call logs.
- Dynamic exception investigation with explicit hypotheses and self-challenge.
- Rule-level financial invariant results with evidence IDs.
- Evidence graph per transaction, including investigation, decision, and evidence nodes.
- Risk scoring and review prioritization fields.
- Verification stage before final decision.
- Human-review and unresolved states.
- Independent evaluator with accuracy, precision, recall, F1, false-positive and false-negative rates, throughput, median/p95/p99 latency, cost/tool metrics, failure taxonomy, and financial impact metrics.
- FastAPI endpoints for datasets, controller runs, reconciliation cases, exceptions, evidence, graphs, audit trail, evaluation, and demo mode.

## Quick Start

Use Python 3.11+.

```powershell
python -m pip install -r requirements.txt
python scripts/demo_run.py --mode MIXED --records 1000 --seed 42
```

The demo writes source CSVs plus a compact `controller_run.json`, `evaluation_report.json`, and `latest_summary.json` under `data/demo/`. Use `--write-full-run` only when you need every case graph and tool call in JSON.

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

Compare deterministic-only and AI-assisted modes:

```powershell
python scripts/compare_controllers.py --records 1000 --mode MIXED --seed 42
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
- `POST /evaluation/compare`
- `GET /evaluation/runs/{id}`
- `GET /evaluation/runs/{id}/failures`
- `POST /demo`

## Architecture

See [docs/architecture.md](docs/architecture.md), [docs/agent_design.md](docs/agent_design.md), [docs/evaluation.md](docs/evaluation.md), and [docs/security.md](docs/security.md).

The implementation separates:

- deterministic finance engine
- bounded investigation tools
- AI-assisted hypothesis layer
- financial invariant engine
- risk scoring
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
- External LLM calls are intentionally disabled by default; the local provider is offline and structured.
- Razorpay test-mode adapters are planned but not required for the local demo.
