# Galarix Integration Boundary

Auditra does not use Galarix as the product. Galarix remains an engineering reference only.

| Component | Purpose | Decision | Reason | Risk |
| --- | --- | --- | --- | --- |
| Intent extraction | Prompt to structured world spec | Reimplement | Auditra needs finance-specific schema and validation | Low |
| Schema registry | Entity schema preview | Reimplement | Current schema is small, typed, and canonical | Low |
| Ontology graph | Relationship model | Reimplement/adapt concept | Auditra graph must map to finance records and evidence | Low |
| Constraint validation | World validation | Reimplement | Financial invariants require Decimal and domain rules | Medium |
| Anomaly generation | Controlled stress cases | Reimplement/adapt concept | Ground truth must remain isolated from controller | Medium |
| Entity resolution | Payment/order/settlement linking | Auditra-owned | Existing reconciliation tools already implement this boundary | Low |
| Product narrative/UI | Not reused | Reject | Auditra is CREATE -> STRESS -> AUDIT -> PROVE | Low |

No Galarix branding, routes, UI, or unrelated architecture are exposed in Auditra.
