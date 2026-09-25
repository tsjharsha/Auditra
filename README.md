# 🛡️ Auditra: Zero-Trust Verification Fabric

> *"Writing code is no longer the bottleneck. Trust is."*

Welcome to **Auditra (The Aegis Protocol)**. Built for the **IBM Bob 2.0 Hackathon**.

Auditra is not an "AI code reviewer" or a "documentation generator." It is an **Adversarial Verification Sandbox** designed to prove that AI-generated code is mathematically flawless before it touches a production system.

## 🚨 The $100 Million Problem
The biggest unsolved problem in enterprise software (Banks, Fintechs, Fortune 500s) is trust. If an AI writes payment routing logic and hallucinates a floating-point rounding error, the bank loses millions of dollars. No enterprise trusts an LLM to write core financial ledgers blindly.

## ⚔️ The Solution: The Aegis Protocol
We built the **Aegis Protocol**: an autonomous immune system for AI-generated code. It acts as a live Pull Request (PR) defense grid against hallucinating or malicious AI agents. 

When bad code enters the system, Auditra intercepts it, runs adversarial synthetic scenarios, detects mathematical drift using SHA-256 cryptographic hashing, prompts an LLM to author a patch, and hot-reloads the server on the fly. 

### The 4-Node Microservice Gauntlet
The demo simulates an enterprise banking cluster with 4 critical microservices. Each node is injected with a different class of AI hallucination:
1. **Tax Router:** Basic logic hallucination (hardcoded flat tax rate instead of state-based parsing).
2. **Billing Engine:** Floating-point precision drift (Penny-shaving "Office Space" bug).
3. **Ledger Sync:** Unauthorized negative-refund exploits (Missing bounds checks).
4. **Fraud Detector:** Scientific-notation string parsing bypasses (`1e9` injection).

---

## 🚀 Running the Aegis Grid

### 1. Backend Setup (FastAPI)
Navigate to the root directory and activate your virtual environment:
```bash
# Windows
.\.venv\Scripts\Activate.ps1

# Install requirements (including Groq for Live LLM mode)
pip install -r requirements.txt groq python-dotenv

# Run the Uvicorn server (HOT RELOAD IS REQUIRED for the demo)
python -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002 --reload
```

### 2. Frontend Setup (React/Vite)
Navigate to the frontend directory:
```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5174` in your browser.

---

## 🎬 How to Perform the Live Demo
1. Click **Reset Grid** (This automatically injects the 4 critical vulnerabilities into the 4 microservices on disk).
2. Click **Launch Grid**.
3. Watch the system autonomously cycle through the 4 nodes. It will detect the drift, display the cryptographic mismatch, prompt the LLM, write the patch directly to the Python AST, hot-reload the server, and mathematically seal the node to Green.

---

## 🧠 Dual-Mode LLM Engine (Mock vs Live)

Auditra features a **Hybrid Engine** for stage presentations:
*   **Demo Mode (Default):** Runs lightning-fast, pre-calculated patches. Used for flawless stage presentations without relying on conference Wi-Fi or unpredictable LLM lag.
*   **Live AI Mode (Groq LLaMA-3):** If a judge wants to see the real engine at work, simply add your Groq API key.

**To enable Live AI Mode:**
Create a `.env` file in the root directory:
```env
GROQ_API_KEY="gsk_your_real_key_goes_here"
```
Auditra will automatically detect the key, ping the Groq API with the cryptographic failure fingerprint, parse the LLaMA-3 response, and apply the real LLM-generated AST patch to the codebase.

---

### Built for the IBM Bob 2.0 / Gateway AI Buildathon
*Breaking reality. Securing the enterprise.*