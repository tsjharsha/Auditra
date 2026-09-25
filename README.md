# AUDITRA
## The Zero-Trust Verification Fabric for AI-Generated Code

Built for **Gateway AI Buildathon 2026, Track 04: AI Finance Controller**.

> **"Everyone else built an AI to write code. We built the system that makes it safe to deploy."**

Enterprises don't have a code generation problem; they have a trust problem. If IBM Bob 2.0 writes a payment routing algorithm that hallucinates a floating-point rounding error, the bank loses $50 million and the C-suite goes to jail.

Auditra is the adversarial verification sandbox that PROVES the code written by IBM Bob 2.0 is mathematically flawless.

![Auditra War Room](docs/assets/submission_flow.svg)

---

### How it Works: The Particle Accelerator for Code

1. **The Target**: IBM Bob 2.0 generates a microservice (e.g., `billing_engine.py`).
2. **The Matrix**: Auditra loads the AI-generated code and violently bombards it with a "Peak Black Friday" load of synthetic adversarial transactions (micro-pennies, floating-point boundaries, massive whales).
3. **The Oracle**: Every output is verified against a Cryptographic Deterministic Oracle that uses pure Banker's Rounding and issues a SHA-256 state hash.
4. **The Autonomous Loop**: If the execution hash and Oracle hash drift by a single byte (e.g., a 0.001 cent fractional rounding leak), the loop halts, extracts the failure fingerprint, and forces IBM Bob 2.0 to autonomously patch the code.
5. **The Certificate**: The loop repeats until the code survives up to 10,000 adversarial scenarios and earns the Cryptographic Oracle Seal of Approval.

### The Float-Drift Bug (The "Office Space" Hack)

In our live demo, IBM Bob 2.0 optimizes the billing engine by using standard `float` math instead of strict `Decimal` precision. This causes a fractional penny drift that is invisible on single tests but lethal at scale.

Auditra's fuzzer explicitly hunts for floats like `.045` or `.505` to trigger the rounding divergence, catching the bug and forcing the AI to patch it using `ROUND_HALF_EVEN`.

### Running the Live War Room

```bash
# Terminal 1: Start the Verification Matrix backend
python -m uvicorn backend.auditra.api:app --host 127.0.0.1 --port 8002

# Terminal 2: Launch the War Room Interface
cd frontend
npm install
VITE_AUDITRA_API_BASE="http://127.0.0.1:8002" npm run dev
```

Open `http://127.0.0.1:5174` and click **Launch Matrix**.

---

### We Don't Trust AI. We Measure It.