# GitHub Submission Metadata

Use these values on the public Auditra repository before submission.

- Repository description: Auditra: an AI Finance Controller for Razorpay-style payment reconciliation
- Topics: razorpay, fintech, reconciliation, payments, ai-controller, finance-operations, fastapi, react, buildathon
- Default branch: main
- Public entry point: README.md
- Demo script: docs/final_demo_script.md
- Architecture: docs/assets/auditra_architecture.svg
- Submission flow: docs/assets/submission_flow.svg
- Evidence path: artifacts/real_groq_smoke.json for the latest reproducible run, with artifacts/real_groq.json retained as historical evidence

## Release Hygiene

Before the final share:

1. Confirm the repository is public and the default branch is main.
2. Confirm no .env, API key, local database, or machine-specific path is committed.
3. Run python -m unittest discover -s tests -v.
4. Run npm run build inside frontend/.
5. Refresh screenshots with scripts/capture_phase_d_screenshots.ps1 if Chrome is available.
6. Link the repository, demo video, and this README in the buildathon submission form.

GitHub repository settings and the demo video are external submission actions; this document records the exact handoff without pretending Codex changed account-level metadata.