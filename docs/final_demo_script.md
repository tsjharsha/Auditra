# Final Five-Minute Demo Script

Target: five minutes. Use the default Payment settlement close scenario with 500 records and seed 42.

## 0:00 - 0:25: The Job

Open the Close page.

Say: "Auditra is a payment operations controller. It reconciles a settlement batch across payments, fees, refunds, and settlements, then brings only the decisions that need attention to a reviewer."

Select Payment settlement close. Keep 500 records selected.

## 0:25 - 0:50: Build The Controlled Batch

Click Build batch.

Say: "The batch is synthetic and repeatable, but its truth labels are locked. The controller cannot see the expected answer before it makes a decision."

Point out the execution disclosure: offline structured mode is reproducible without a provider key; live-provider mode is labeled only when real calls occur.

## 0:50 - 1:35: Run The Audit

Click Run audit.

Say: "The controller applies deterministic money controls first. Bounded AI can investigate ambiguous cases, but it cannot perform authoritative math or override verification."

After the result appears, point out only four numbers:

- Match rate
- Needs review
- At-risk amount
- Throughput

## 1:35 - 2:30: The One Exception

Open Inspect evidence on the priority decision.

Say: "This is the decision that matters: the expected and actual settlement do not tie out. Auditra shows the variance, the supporting payment/refund/settlement evidence, and whether deterministic checks agree."

On Review, show the evidence and verification sections.

Say: "A reviewer can approve, reject, or keep this open. The review event records the configured reviewer identity."

## 2:30 - 3:10: Honest Measurement

Return to Close and point to Close assurance, then open Audit.

Say: "The controller is evaluated after the run against hidden ground truth. We report exact status accuracy, macro F1, missed-exception rate, financial impact, and the cases that still differed from truth."

Important disclosure:

- The default demo is an offline structured controller with zero external calls.
- The separate Groq artifact is PARTIAL_RATE_LIMITED, not a full external-LLM claim.
- A real-provider run is only called fully real when its artifact is PASS_FULL_REAL.

## 3:10 - 4:15: Attack The Weakness

On Audit, show the assurance verdict and launch the targeted retest.

Say: "One good batch is not enough. Auditra fingerprints the measured failure pattern, generates an adversarial retest around it, and changes its deployment recommendation based on the result."

Point out the assurance score, unsafe auto-actions, failure fingerprint, and retest verdict.

## 4:15 - 5:00: Close

Return to Close and click Audit report or Exception CSV.

Say: "Auditra closes one finance-ops loop over more than 50 records and exports the evidence. It does not ask Razorpay to trust an AI controller. It measures whether the controller should be trusted."

## Judge Questions

### Is this actually AI?

AI is bounded to interpreting setup and investigating ambiguous exceptions. Settlement arithmetic, controls, invariants, verification, and assurance are deterministic. The UI discloses whether a run used an offline structured investigator or a real provider.

### Why synthetic data?

Track 04 requests synthetic data. Synthetic batches make the demo safe, repeatable, and measurable against hidden ground truth.

### Why show failures?

Finance controllers must report uncertainty honestly. Auditra lists open exceptions, financial exposure, and measured errors, then retests the failure pattern.
