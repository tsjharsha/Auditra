# Built with IBM Bob 2.0

Auditra was developed using IBM Bob as the primary AI-assisted development environment.

Bob was used for:
* **Repository-level reasoning**: Understanding the complex financial data flows in the original legacy repository.
* **Architecture iteration**: Moving from a generic LLM app to a zero-trust verification engine.
* **Backend implementation**: Writing the FastAPI streaming endpoints and the AST Validator.
* **Frontend implementation**: Building the React War Room, SSE stream parsing, and visual state machines.
* **Security hardening**: Iterating on the `sandbox.py` subprocess execution model.
* **Documentation**: Structuring the product narrative.

## The Meta-Story
> **The project built with AI is itself protected by an AI verification system.**

IBM Bob generated the backend systems, and then Auditra's deterministic Oracle was used to independently test that code for edge-case failures. Bob iteratively proposed corrections, and Auditra verified those corrections mathematically. This demonstrates Bob's power in a real developer workflow.

## IBM Bob MCP Integration

Auditra exposes its deterministic Oracle to IBM Bob via the Model Context Protocol (MCP), providing two verification-only tools:

* **`verify_target`**: Verifies the current implementation of one target against Auditra's existing independent verification/oracle pipeline.
* **`verify_all`**: Verifies all current target implementations and runs the mutation suite.

**Scope of `verify_all`**
* An `APPROVED` result from `verify_all` means the current implementations passed the verification suite and mutation testing.
* `verify_all` is strictly a **verification-only gate** exposed to IBM Bob.
* It does **NOT** represent completion of the full AEGIS lifecycle of AI patch generation, AST validation, patch application, post-patch verification, rollback, and final release gating.
