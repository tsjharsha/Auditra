# Final Auditra Architecture

Auditra follows this product loop:

```text
PROMPT -> WORLD -> STRESS -> AUDIT -> INVESTIGATION -> EVIDENCE -> VERIFICATION -> EVALUATION
```

![Auditra architecture](assets/auditra_architecture.svg)

## Runtime Flow

1. `WorldUnderstandingService` converts natural language into a typed `FinancialWorldSpec`.
2. `financial_world.schema` returns the canonical schema and relationship preview.
3. `FinancialWorldGenerator` deterministically creates merchants, orders, payments, settlements, refunds, fee rules, and hidden anomaly truth.
4. `WorldValidator` checks referential integrity, currencies, merchant consistency, timing, refunds, fee rules, and duplicate patterns.
5. `DatasetIndex` strips hidden ground truth and prepares the visible finance graph.
6. `ReconciliationEngine` runs deterministic controls.
7. `AIInvestigationAgent` adds bounded hypotheses, tool traces, self-challenge, and verification to exception cases.
8. `IndependentEvaluator` compares controller output with hidden ground truth after the run.
9. The frontend exposes CREATE -> STRESS -> AUDIT -> PROVE as one local product experience.

## Trust Boundaries

- The controller receives visible records only.
- Hidden ground truth is used only by the evaluator.
- AI providers produce structured specs or investigation plans, not final financial truth.
- Decimal arithmetic, expected settlement math, and invariant checks remain deterministic.
- Evidence tools are allowlisted and reject unknown or non-public entities.
- Tool failures escalate to human review rather than crashing or auto-resolving.
- PostgreSQL support separates visible datasets from `ground_truth_cases`.

## Modules

- `backend/auditra/financial_world/`: world builder, schema, ontology, adapters, validation.
- `backend/auditra/reconciliation.py`: deterministic controls and AI-assisted case handling.
- `backend/auditra/agent_tools.py`: typed, logged investigation tools.
- `backend/auditra/invariants.py`: financial invariant engine.
- `backend/auditra/evidence_graph.py`: graph with source, investigation, decision, and evidence nodes.
- `backend/auditra/evaluator.py`: independent measurement.
- `backend/auditra/postgres.py`: optional PostgreSQL repository.
- `frontend/src/`: product UI.
