import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .verification_api import router as verification_router

app = FastAPI(
    title="Auditra: The Aegis Protocol",
    version="1.0.0",
    description="Adversarial Verification Sandbox for AI-generated code.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "AUDITRA_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174,http://127.0.0.1:4173,http://localhost:4173",
        ).split(",")
        if origin.strip()
    ],
    allow_origin_regex=os.getenv("AUDITRA_CORS_REGEX", r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(verification_router)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "mode": "demo" if not os.environ.get("GROQ_API_KEY") else "live",
        "verification_engine": "ready"
    }
