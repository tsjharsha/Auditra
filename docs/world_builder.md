# Financial World Builder

The Financial World Builder turns natural language into a deterministic financial test world.

## Input

Example:

```text
Generate an Indian e-commerce merchant with 500 orders, UPI and card payments, 2% platform fees, T+2 settlement, refunds, partial settlements and realistic reconciliation anomalies.
```

## Structured Spec

The prompt becomes `FinancialWorldSpec`:

- merchant name and country
- record count
- seed
- currencies
- payment methods
- fee rate and fixed fee
- settlement delay
- refund rate
- anomaly mode
- anomaly rates

## Generation

Generation is deterministic from:

```text
prompt + normalized specification + seed
```

The generator creates:

- merchants
- orders
- payments
- settlements
- refunds
- fee rules
- hidden ground truth cases

## Validation

Before exposure, the validator checks:

- referential integrity
- currency consistency
- merchant consistency
- temporal consistency
- refund constraints
- fee rules
- duplicate constraints

Controlled anomalies are warnings when they are intentionally injected and tracked in hidden truth.
