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
