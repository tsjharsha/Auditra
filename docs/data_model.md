# Data Model

## Canonical Records

- `Merchant`
- `Order`
- `Payment`
- `Settlement`
- `Refund`
- `FeeRule`

All money values use `Decimal` quantized to two places. All operational timestamps are timezone-aware.

## Control Records

- `FinancialWorldSpec`
- `WorldSummary`
- `WorldValidationReport`
- `ReconciliationCase`
- `ControllerDecision`
- `InvariantResult`
- `AIInvestigationResult`
- `InvestigationHypothesis`
- `EvidenceItem`
- `EvidenceGraph`
- `EvaluationRun`
- `FailureRecord`

## Ground Truth

`DatasetBundle.ground_truth` contains hidden labels for evaluation only. Public world, controller, graph, evidence, and API payloads do not expose it.

## PostgreSQL

The production migration is in `migrations/001_initial_postgres.sql`. It includes tables for canonical records, transaction links, cases, investigations, hypotheses, evidence, tool calls, decisions, verification, audit events, evaluation runs, ground truth, and human reviews.
