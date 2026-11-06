"""
main.py
────────
FastAPI application entry point.

Routes
──────
  GET  /api/health    – liveness probe
  GET  /api/profile   – public profile data (safe for browsers)
  POST /api/chat      – primary AI chat endpoint

Run locally
───────────
  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

Or via the helper script at the project root:
  python -m backend.main
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import API_KEY, HOST, MODEL, PORT, URL
from backend.schemas import ChatRequest, ChatResponse, PublicProfile
from backend.services.llm_engine import generate_response
from backend.services.profile_loader import get_public_profile_dict, reload_profile

# ── Paths ──────────────────────────────────────────────────────────────────────
from pathlib import Path
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: warm the profile cache so the first request is not slower.
    Shutdown: nothing to clean up (httpx clients are created per-request).
    """
    logger.info("Starting AboutMe AI backend…")
    try:
        reload_profile()           # validate profile.json is readable
        get_public_profile_dict()  # warm cache
        logger.info("Profile loaded successfully.")
        provider_name = (
            "OpenRouter" if "openrouter.ai" in URL
            else ("Groq" if "groq.com" in URL
            else ("OpenAI" if "openai.com" in URL else "Custom Endpoint"))
        )
        logger.info("Active LLM Provider: %s (%s)", provider_name, URL)
        logger.info("Active LLM Model: %s", MODEL)
    except FileNotFoundError as exc:
        logger.error("FATAL: %s", exc)
        raise SystemExit(1) from exc
    yield
    logger.info("AboutMe AI backend shutting down.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AboutMe – Amirreza Dorosti's AI-Native Portfolio API",
    description=(
        "Strict-grounding, zero-hallucination AI backend for Amirreza Dorosti's "
        "personal portfolio. All facts are sourced from profile.json or the "
        "GitHub REST API v3. Phone number and other private data are refused."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Allow all origins so the frontend can be served from any domain
# (Hamravesh CDN, localhost dev, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # must be False when allow_origins=["*"]
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Serve frontend static files ────────────────────────────────────────────────
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIR)), name="static")


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please try again."},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.get(
    "/api/health",
    summary="Liveness probe",
    tags=["Infra"],
)
async def health_check() -> dict[str, Any]:
    """Returns 200 OK and active provider info when the server is running."""
    provider_name = (
        "OpenRouter" if "openrouter.ai" in URL
        else ("Groq" if "groq.com" in URL
        else ("OpenAI" if "openai.com" in URL else "Custom Endpoint"))
    )
    return {
        "status": "healthy",
        "service": "AboutMe AI Backend",
        "provider": provider_name,
        "url": URL,
        "base_url": URL,
        "model": MODEL,
    }


@app.get(
    "/",
    include_in_schema=False,
)
async def serve_index() -> FileResponse:
    """Serve the main frontend HTML page."""
    index_path = _FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(str(index_path))


@app.get(
    "/api/profile",
    response_model=PublicProfile,
    summary="Retrieve Amirreza Dorosti's public profile",
    tags=["Profile"],
)
async def get_profile() -> PublicProfile:
    """
    Returns the sanitised public profile loaded from data/profile.json.
    Private fields (phone number) are never included.
    The frontend uses this endpoint to render the static portfolio sections.
    """
    try:
        data: dict[str, Any] = get_public_profile_dict()
        return PublicProfile(**data)
    except Exception as exc:
        logger.exception("Failed to load profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not load profile data.",
        ) from exc


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Send a question to Amirreza Dorosti's AI assistant",
    tags=["Chat"],
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Primary chat endpoint.

    Request body
    ─────────────
      question              – visitor's question (1–2000 chars)
      conversation_history  – list of prior {role, content} turns (optional)

    Response
    ─────────
      answer  – the human-readable answer
      trace   – full explainability audit record including:
                  intent, capability, fields_read, missing_facts,
                  external_service_used, audit_spans (Idea 1: Grounding Auditor)

    Guardrails enforced
    ────────────────────
      • Phone number requests → refuse_fact (caught before LLM call)
      • Booking / email requests → refuse_fact (enforced by LLM system prompt)
      • Speaking for Sharif University → refuse_fact (enforced by LLM system prompt)
      • Ambiguous project reference → ask_clarification (enforced by LLM)
      • Missing record fields → missing_fact_notice in audit_spans
    """
    history = [turn.model_dump() for turn in request.conversation_history]

    response: ChatResponse = await generate_response(
        question=request.question,
        conversation_history=history,
    )
    return response


# ── Dev server entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
