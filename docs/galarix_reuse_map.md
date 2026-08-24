# Galarix Reuse Map

Reference inspected: `https://github.com/tsjharsha/Galarix`

Cloned commit: `e7de7df0edfe2e39201c0b95e68da45730c8f868`

Important licensing note: the cloned repository does not include a top-level `LICENSE` file. Auditra therefore avoids copying Galarix source code directly. The implementation in this repo reimplements domain-specific Auditra logic and only adapts architectural ideas where useful.

| Component | Purpose | Auditra use | Reuse / Adapt / Reimplement / Ignore | Dependencies | Risk |
|---|---|---|---|---|---|
| `fintech-backend/app.py` | Flask API, Firebase auth, SSE synthetic-data endpoints | Not relevant to Auditra's bounded finance controller API | Ignore | Flask, Firebase, Flasgger, Groq | Tightly branded and product-coupled |
| `fintech-backend/pipeline.py` | Stage orchestration with safe fallbacks | Inspiration for a single controller entrypoint | Adapt | Stage 1 and 1.5 modules | Good pattern, but not finance reconciliation |
| `stage_1/agentic_retriever.py` | LLM query expansion for prompts | No authoritative finance decisions; optional future exception summarization only | Ignore for core | Groq, httpx, certifi | External LLM dependency and prompt-domain coupling |
| `stage_1/entity_resolver.py` | Layered deterministic entity scoring | Pattern adapted for exact/composite financial entity linking | Adapt | Keyword constants, agentic retriever | Must not silently fuzzy-link financial records |
| `stage_1/confidence_scorer.py` | Weighted confidence from multiple factors | Pattern adapted as evidence-quality confidence | Adapt | Constants | Original factors are prompt-centric |
| `stage_1/contract_builder.py` | Stage 1 orchestrator | Pattern adapted for controller case assembly | Adapt | Stage 1 modules | Debug printing and prompt assumptions not reused |
| `stage_1/intent_extractor.py` | Extract scale/risk/frequency from prompts | Not needed for transaction reconciliation | Ignore | Regex constants | Prompt parser is unrelated |
| `stage_1/variable_mapper.py` | Synthetic entity to variable registry | Auditra defines fresh typed finance schemas | Reimplement | Hard-coded variable registry | Domain mismatch |
| `stage_1/temporal_intent_extractor.py` | Time-series parsing and horizon extraction | Settlement timing windows and calendar ideas | Adapt selectively | Regex/date logic | Contains a `q` vs `quarter` bug in quarter-specific path |
| `stage_1_5/ontology_graph.py` | Entity dependency map | Pattern adapted into evidence graph relationships | Adapt | Static dictionaries | Galarix entities are synthetic-data domains |
| `stage_1_5/schema_registry.py` | Single source of truth for schemas and data provenance | Pattern only; Auditra uses fresh order/payment/settlement/refund/fee models | Reimplement | Large static registry | Very product/domain specific |
| `stage_1_5/contract_validator.py` | Structural validation and default repair | Pattern adapted into Pydantic validation and controller verification | Adapt | Constants | Silent repair is risky for finance; Auditra records exceptions |
| `stage_1_5/entity_guarantor.py` | Ensure valid entity after parsing | Reimplemented as explicit missing-link handling | Reimplement | Constants | Finance cannot default missing entities silently |
| `stage_1_5/enrichment_engine.py` | Normalize, default, guarantee, validate, attach schema | Pattern adapted as normalize -> reconcile -> verify pipeline | Adapt | Stage 1.5 modules | Original pipeline mutates synthetic contracts |
| `stage_1_5/intent_validator.py` | Clamp prompt intent values | Not core | Ignore | Constants | Prompt-only |
| `stage_1_5/synonym_normalizer.py` | Safe word-boundary synonym normalization | Possible future CSV header normalization | Adapt later | Regex constants | Useful pattern, not needed in first slice |
| `stage_2/dependency_engine.py` | Standardize conditionals/correlations/derived formulas | Reimplemented as financial invariants | Reimplement | None | Original is shallow and schema-specific |
| `stage_2/constraint_engine.py` | Attach mathematical bounds to generated distributions | Reimplemented as Decimal amount/timestamp invariants | Reimplement | math | Distribution constraints do not map directly |
| `stage_2/covariance_engine.py` | Synthetic correlation hints | Not relevant to reconciliation correctness | Ignore | NumPy later in pipeline | Could create misleading finance links |
| `stage_2/temporal_model_compiler.py` | Calendar, regime, seasonality, autocorrelation model | Settlement timing and holiday-calendar ideas | Adapt selectively | Pure Python data structures | Much of it is market time-series specific |
| `stage_2/behavior_mapper.py` | Prompt intent to mathematical tensors | Not relevant | Ignore | Tensor engine | Prompt synthetic-data coupling |
| `stage_2/validator.py` | Validate generated statistical model parameters | Pattern adapted into verification layer | Adapt | None | Original validates distributions, not money movement records |
| `stage_3/anomaly_injector.py` | Seeded clustered anomaly injection | Pattern adapted into scenario/evaluation generator | Adapt | NumPy | Original anomaly labels are generated-data specific |
| `stage_3/constraint_enforcer.py` | Final pass enforcing bounds and domain guards | Pattern adapted into deterministic reconciliation verification | Adapt | NumPy | Finance controls must not silently clamp source records |
| `stage_3/correlation_weaver.py` | Cholesky copula for synthetic correlations | Not used | Ignore | NumPy | Unnecessary and could obscure evidence |
| `stage_3/temporal_anomaly_engine.py` | Time-aware anomaly injection | Pattern adapted for timing anomalies and clustered exceptions | Adapt | NumPy | Market anomaly types not reused |
| `stage_3/temporal_consistency_auditor.py` | Post-generation temporal quality audit | Pattern adapted into evaluation metrics and timing checks | Adapt | NumPy | Needs finance-specific checks |
| `stage_3/quality_auditor.py` | Statistical audit and quality score | Pattern adapted into independent evaluator | Adapt | NumPy | Distribution tests are not Auditra's target metric |
| `stage_3/generation_orchestrator.py` | Seed -> generate -> inject -> enforce -> audit -> certify | Strong orchestration precedent | Adapt | Many stage modules | Original is too broad to import |
| `trust_engine/provenance_certifier.py` | Build provenance chain with source citations | Pattern adapted into evidence items and audit trail | Adapt | Regional benchmark registry | Sources are distribution provenance, not transaction evidence |
| `trust_engine/statistical_validator.py` | Formal tests for generated data | Pattern adapted into independent evaluation metrics | Adapt | NumPy | Uses `eval` for formulas; not suitable for controller decisions |
| `trust_engine/trust_report_builder.py` | Weighted trust certificate | Pattern adapted into evaluation report | Adapt | ReportLab optional | Galarix branding and synthetic-data scoring not reused |
| `fintech-synthetic-ui/*` | Galarix synthetic-data frontend | Not used | Ignore | React/Firebase assets | Product narrative and UI are forbidden for Auditra |

## Summary

High-value reusable ideas:

- Deterministic first, agent second.
- Layered resolution with explicit confidence factors.
- Single schema/source-of-truth discipline.
- Seeded scenario generation and anomaly injection.
- Final verification/audit pass before declaring trust.
- Public metrics that show failures rather than hiding them.

Rejected carryover:

- Galarix branding, UI, routes, Firebase auth, Flask app, synthetic-data schemas, prompt expansion, Groq dependence, and statistical generation pipeline.
