# Auditra
### Zero-Trust Verification Fabric for AI-Generated Software

**AI proposes. Auditra verifies.**

AI coding tools increase development velocity, but generated code still requires validation, regression testing, and review. **Auditra creates an automated verification gate between generated code and deployment.**

Don't trust generated code. Test it adversarially. Verify it independently. Accept it or roll it back.

---

## 1. What is Auditra?
Auditra is an adversarial verification engine that acts as a production gate for AI-generated code. Instead of trusting an LLM's patch proposal, Auditra explicitly sandboxes the code, runs deep regression and boundary tests, compares the output against a deterministic Oracle, and either automatically merges the patch or rejects and rolls it back.

## 2. Why does it exist?
The current AI-assisted development workflow looks like this:
`AI -> Developer Review -> Tests -> Debugging -> Regression -> Merge`

Auditra compresses this into:
`AI -> Auditra adversarial verification -> AI repair -> Automated reverification -> Production Gate`

## 3. What makes it different?
Most "AI Code Review" tools are purely probabilistic—they use an AI to review an AI. Auditra enforces an explicit **Trust Boundary**. The AI reasoning is isolated from the deterministic verification. **The AI can recommend, but the Oracle decides.**

## 4. How does it verify code?
Auditra generates test inputs across four categories:
* **Normal cases**
* **Boundary cases**
* **Adversarial cases**
* **Regression cases**

It runs these inputs through both the AI-patched code (in a strict Sandbox) and a hidden, known-good Oracle. If the outputs diverge, the code is compromised.

## 5. What happens when AI is wrong?
The patch is immediately rejected. A live diff is generated, the failure reason is exposed to the developer (e.g., "Oracle expected X, observed Y"), and a file-level **ROLLBACK** is performed to restore the secure state. The system never ships unsafe code.

## 6. What does IBM Bob have to do with it?
Auditra was built entirely using **IBM Bob 2.0** as the primary AI-assisted development environment. IBM Bob iterated on the architecture, wrote the AST Validator, built the React frontend, and implemented the Sandbox. 

This creates a powerful meta-story: **The project built with AI is itself protected by an AI verification system.** See [Built with Bob](docs/bob-usage.md) for details.

## 7. How do I run it?

**CI/CD Verification Gate (CLI)**
```bash
python -m backend.auditra verify --json
```
*Exit code 0: Safe to deploy.*
*Exit code >0: Block merge/deployment.*

**Interactive War Room (Frontend Demo)**
```bash
# Terminal 1
python -m uvicorn backend.auditra.api:app --port 8002

# Terminal 2
cd frontend
npm run dev
```
Open `http://localhost:5173`. Click **Reset Environment**, then **Launch Verification Grid**.

## 8. What is actually demonstrated?
The demo runs against four deliberately vulnerable financial microservices (where behavioral errors have direct monetary consequences). 
1. **Tax Router**: Detects hardcoded rates.
2. **Billing Engine**: Evaluates unsafe float arithmetic.
3. **Ledger Sync**: Validates negative refund bounds.
4. **Fraud Detector**: Intentionally demonstrates a **ROLLBACK** when the AI proposes an incorrect threshold.

## 9. Limitations
* Auditra currently verifies behavior against explicit deterministic scenarios and does not mathematically prove arbitrary program correctness.
* The current sandbox is designed for controlled demonstration workloads and is not a replacement for a hardened production container/VM boundary.
* Verification quality is bounded by oracle quality and scenario coverage.