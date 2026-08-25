# Phase B Report

Date: 2026-08-25

## Scope

Phase B productized Auditra into a Vite, React, TypeScript and Tailwind application backed by the existing FastAPI service. The work preserved the Phase A financial controls and added a premium demo path around real backend objects instead of static mock screens.

## Screens Built

- Home: Auditra identity, prompt workbench, `BUILD FINANCIAL WORLD`, `USE DEMO WORLD`, and `RUN 5-MINUTE DEMO`.
- World Builder: prompt understanding, editable `FinancialWorldSpec`, schema browser, relationship graph, generation, validation, and audit transition.
- World Explorer: searchable/sortable/paginated merchants, orders, payments, settlements, refunds and fee rules from the backend public dataset.
- Reconciliation: controller progress, metrics dashboard, exception queue, all-case table, and AI-vs-baseline comparison.
- Investigations: selected case hero, hypotheses, verification, final decision, tool trace, evidence list, source record view and case evidence graph.
- Evidence Graph: case selector and React Flow graph for transaction-level evidence.
- Human Review: review queue and live `APPROVE`, `REJECT`, `MARK_UNRESOLVED` backend actions.
- Evaluation Lab: controlled anomaly settings, stress modes, break-controller action, comparison charts, failure taxonomy, confusion matrix and failure replay.
- Controller Runs: in-session controller run history.
- Audit Trail: controller audit events and recorded review feedback.

## UX Decisions

- Empty, loading, success and error states are explicit so no screen pretends data exists before the backend creates it.
- Navigation mirrors the requested demo storyline: build the world, explore records, audit, investigate, review, evaluate, then inspect run/audit history.
- Tables are dense and operational, with search, sorting, pagination and click-through detail views for repeated controller workflows.
- The visual system uses restrained fintech colors with teal, indigo, amber and rose accents for control health, review state, warnings and failures.
- Graph and chart surfaces use React Flow and Recharts so the evidence relationships and measured AI value are visible without hand-rolled visualization logic.

## Architecture

- `frontend/src/api`: typed API client for the FastAPI endpoints.
- `frontend/src/hooks`: `AuditraProvider` holds the current world, audit result, selected case, comparison and run history.
- `frontend/src/pages`: route-level product screens.
- `frontend/src/features`: world builder/explorer, audit, graph, investigation and evaluation modules.
- `frontend/src/components/ui`: small reusable controls for cards, buttons, badges, tables, metrics, states, tabs and fields.
- Backend change: `FinancialWorldService.public_dataset()` now exposes safe source records for explorer screens while still excluding `ground_truth`, `expected_status`, `scenario` and anomaly labels.

## Demo Path

1. Open `http://127.0.0.1:5173/`.
2. Click `Run 5-Minute Demo` or `Use Demo World`.
3. Inspect Reconciliation metrics and exceptions.
4. Open an exception to view hypotheses, evidence, verification and tool calls.
5. Move to Human Review and record a reviewer action.
6. Open Evaluation Lab, run AI-vs-baseline comparison, then run a stress mode or `Break Controller`.
7. Check Controller Runs and Audit Trail.

## Validation

- `npm run build`: passed. Vite reported a large chunk warning caused by chart and graph dependencies.
- `python -m unittest discover -s tests -v`: 25 tests passed with 2 FastAPI tests skipped in the default interpreter.
- `py -3.13 -m unittest discover -s tests -p test_api.py -v`: 2 API tests passed.
- Live API smoke confirmed the existing 8000 server was healthy, but it was an older running process; a fresh backend process is needed to serve the new public record payload.

## Limitations

- Run history is in-memory in the browser session and reflects runs performed during the current visit.
- Human review records are submitted to the backend, but the reviewed case status is not rewritten in-place by the current API.
- The frontend bundle is large because React Flow and Recharts are loaded eagerly. Code splitting is a good next optimization.
- The app defaults to the offline structured AI path unless OpenAI environment variables are configured for the backend.
