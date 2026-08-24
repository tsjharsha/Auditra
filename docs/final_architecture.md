# Final Auditra Architecture

Auditra now follows the product loop:

```text
PROMPT -> FINANCIAL WORLD -> STRESS -> AUDIT -> INVESTIGATE -> PROVE
```

## Runtime Flow

1. `financial_world.understanding` converts natural language into a typed `FinancialWorldSpec`.
2. `financial_world.schema` returns the canonical schema and relationship preview.
3. `financial_world.generator` deterministically creates merchants, orders, payments, settlements, refunds, fee rules, and hidden anomaly truth.
4. `financial_world.validation` checks integrity before the world is exposed.
5. `ReconciliationEngine` audits the generated or ingested dataset.
6. `AIInvestigationAgent` investigates exception and low-confidence cases through bounded tools.
7. `IndependentEvaluator` compares controller output with hidden ground truth after the run.
8. The frontend presents CREATE -> STRESS -> AUDIT -> PROVE as one local product experience.

## Trust Boundaries

- The controller receives visible records only.
- `DatasetIndex` strips `ground_truth` before tool access.
- LLM providers produce specifications or investigation plans, not records or financial decisions.
- Decimal arithmetic and verification remain deterministic.
- PostgreSQL support separates visible datasets from `ground_truth_cases`.

## Key Modules

- `backend/auditra/financial_world/`: world builder, prompt parser, schema, ontology, adapters, validation.
- `backend/auditra/reconciliation.py`: deterministic control layer plus AI-assisted investigation attachment.
- `backend/auditra/agent_tools.py`: typed, allowlisted, logged investigation tools.
- `backend/auditra/invariants.py`: financial invariant engine.
- `backend/auditra/evidence_graph.py`: graph with evidence, investigation, and decision nodes.
- `backend/auditra/evaluator.py`: independent measurement.
- `backend/auditra/postgres.py`: optional PostgreSQL repository.
- `frontend/index.html`: product UI for world builder, audit, investigations, review, evaluation, and audit trail.
