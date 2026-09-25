# Auditra: The Zero-Trust Verification Fabric

> **AI can write the code. Auditra proves whether it deserves to run.**

Welcome to **Auditra (The Aegis Protocol)**, built for the **IBM Bob 2.0 / Gateway AI Buildathon**.

## 🚨 The Problem
The biggest unsolved problem in enterprise software (Banks, Fintechs, Fortune 500s) is trust. If an AI writes payment routing logic and inadvertently hallucinates a floating-point rounding error, a bank could lose millions of dollars. No enterprise trusts an LLM to write core financial ledgers blindly.

## ⚔️ The Solution
**AI proposes. Auditra verifies.**

Auditra is an **Adversarial Verification Sandbox** designed to prove that AI-generated code is mathematically flawless before it touches a production system. It acts as an autonomous immune system for AI-generated code.

## 🏗️ Architecture & Verification Lifecycle
Auditra guarantees that code is never blindly accepted from an LLM. The state transitions are explicitly controlled:

```text
ATTACK (Adversarial Fuzzing)
  ↓
DETECT (Cryptographic Hash Mismatch against Oracle)
  ↓
ANALYZE
  ↓
GENERATE PATCH (Untrusted LLM Output)
  ↓
VALIDATE PATCH (AST Syntax + Security Checks)
  ↓
APPLY IN ISOLATED SANDBOX
  ↓
RUN ADVERSARIAL TESTS AGAIN
  ↓
COMPARE AGAINST INDEPENDENT ORACLE
  ↓
PASS?
 ├── YES → SECURE
 └── NO  → PATCH FAILED → ROLLBACK TO KNOWN STATE
```
**Core Invariant:** `PATCH_APPLIED != SECURE`. Code is only marked `SECURE` after a full post-patch adversarial re-verification proves it mathematically satisfies the independent Oracle.

## 🦠 Four Demonstration Nodes
The demo simulates an enterprise banking cluster with 4 critical microservices. Each node is injected with a different class of AI hallucination:
1. **Tax Router:** Basic logic hallucination (hardcoded flat tax rate instead of state-based parsing).
2. **Billing Engine:** Floating-point precision drift (Penny-shaving "Office Space" bug).
3. **Ledger Sync:** Unauthorized negative-refund exploits (Missing bounds checks).
4. **Fraud Detector:** Scientific-notation string parsing bypasses (`1e9` injection).

## 🔒 Threat Model & Security Boundaries
*   **LLM (Untrusted):** Can hallucinate, generate dangerous imports (`os`, `subprocess`), or syntax errors.
*   **Generated Code (Untrusted):** Executed only inside the restricted `SandboxRunner`.
*   **Oracle (Trusted):** The independent, deterministic source of truth.
*   **AST Validator (Trust Boundary):** Strips/rejects arbitrary code execution attempts before they reach the sandbox.
*   **Rollback Engine:** Ensures the target application is never left in an unknown or corrupted state if a patch fails.

## 🧠 IBM Bob 2.0 & LLM Integration
IBM Bob 2.0 was used as the primary development environment and AI coding workflow to *build* the Auditra platform. 

For the live verification engine itself, Auditra operates in one of two modes:
*   **Deterministic Demo Mode (Default):** Runs lightning-fast, pre-calculated patches. Used for flawless stage presentations without relying on conference Wi-Fi.
*   **Live AI Mode (Groq LLaMA-3):** Uses an external LLM to simulate the untrusted AI patching process. 

## 🚀 Running the Aegis Grid

### 1. Backend Setup (FastAPI)
```bash
# Windows
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt groq python-dotenv pytest

# Run the Uvicorn server (HOT RELOAD IS REQUIRED for the demo)
python -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002 --reload
```

### 2. Frontend Setup (React/Vite)
```bash
cd frontend
npm install
npm run dev
```
Open `http://127.0.0.1:5174` in your browser.

## 🎬 How to Perform the Live Demo
1. Click **Reset Environment** (Injects the 4 critical vulnerabilities from `target_templates` to the active disk).
2. Click **Launch Verification Grid**.
3. Watch the system autonomously cycle through the 4 nodes. It will detect the drift, validate the AST, execute in the sandbox, re-verify post-patch, and mathematically seal the node to Green.

## 🧪 Tests
To verify the security invariants (e.g. rejecting dangerous imports, `eval()` usage, and proving `PATCH_APPLIED != SECURE`), run:
```bash
pytest tests/
```