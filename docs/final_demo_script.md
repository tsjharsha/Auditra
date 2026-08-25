# Final Five-Minute Demo Script

Target: 5 minutes or less.

Frozen run: seed `42`, world `FW_0a7d61b20d15`, dataset `WORLD_FW_0a7d61b20d15`.

| Time | Screen | Action | Spoken line | Metric | Transition |
| --- | --- | --- | --- | --- | --- |
| 0:00-0:20 | Home | Open `http://127.0.0.1:5174/` | "Most financial AI demos start with a dataset. Auditra starts one step earlier." | Product loop: CREATE -> STRESS -> AUDIT -> PROVE | Click `Run 5-Minute Demo` |
| 0:20-0:55 | World Builder | Show prompt understanding and generated schema | "The prompt becomes a typed financial world spec, not free-form model output." | 500 orders, INR 2148789.81 payment volume | Open World Explorer |
| 0:55-1:25 | Financial World | Show merchants, orders, payments, settlements, refunds, and fee rules | "The synthetic world is controlled so we can know what the controller should find." | 506 payments, 486 settlements, 60 refunds, 112 anomalies | Open Reconciliation |
| 1:25-2:05 | Controller | Show audit stages and metrics | "The controller audits every transaction with deterministic financial controls and bounded AI investigation." | 99.60% accuracy, 99.21% auto-resolution, 0.79% human review | Open Investigations |
| 2:05-2:50 | Investigation | Select the highlighted review case | "AI investigates exceptions, but evidence and verification remain structured." | 112 AI-investigated cases, 0 external LLM calls by default | Open Evidence Graph |
| 2:50-3:25 | Evidence Graph | Show payment, order, settlement, refund, decision, and verification nodes | "The reviewer can see why a decision happened and which records support it." | Graph evidence is generated from visible records only | Open Human Review |
| 3:25-3:55 | Human Review | Show escalated cases | "When evidence is conflicting or unsafe, Auditra escalates instead of pretending certainty." | 4 human-review cases in the demo run | Open Evaluation Lab |
| 3:55-4:35 | Evaluation Lab | Show AI vs baseline table | "The AI is measured against hidden ground truth after the run." | Baseline failures 15, AI failures 2 | Click Break Controller if time allows |
| 4:35-5:00 | Break The Controller | Show stress run result | "The point is not a perfect demo. The point is a controller that shows where it fails." | Frozen demo error impact INR 647.36 | End on Failure Report |

Closing line:

```text
Auditra explores a problem that becomes increasingly important as financial operations become agentic: how do you verify that financial AI is actually correct?
```
