# One-Minute Technical Version

Auditra has eight layers.

1. World Builder: parses a natural-language finance prompt into a typed `FinancialWorldSpec`.
2. Financial Graph: generates linked merchants, orders, payments, settlements, refunds, fee rules, and evidence edges.
3. Deterministic Controls: computes expected net settlement, refund adjustment, fee rules, duplicate patterns, timing, merchant, and currency checks.
4. AI Investigation: attaches hypotheses and tool traces to exception or low-confidence cases.
5. Evidence: all investigation tools read only public records through allowlisted APIs.
6. Self-Challenge: the AI plan is challenged against alternative explanations such as refunds, fees, duplicates, missing links, and conflicting records.
7. Verification: deterministic invariants decide whether a classification is safe or must be escalated.
8. Evaluation: hidden ground truth is revealed only after the controller run to compute accuracy, precision, recall, F1, latency, cost, failure category, and financial impact.

The LLM can help investigate. It cannot override financial truth.
