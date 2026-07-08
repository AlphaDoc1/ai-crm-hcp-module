"""
app/main.py
─────────────────────────────────────────────────────────────────────────────
FastAPI application entry point.

Registers:
  • CORS middleware (allows React dev server at localhost:3000)
  • /health endpoint
  • All API routers: /api/hcps, /api/interactions, /api/chat, /api/follow-ups
  • Lifespan startup: pre-compiles the LangGraph agent & verifies DB connection
─────────────────────────────────────────────────────────────────────────────
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine, SessionLocal
from app.schemas import HealthResponse
from app.routers import hcps, interactions, follow_ups, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Lifespan: startup / shutdown
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup:
      1. Verify DB connectivity (fail fast if Postgres is down).
      2. Pre-compile the LangGraph agent so the first /api/chat call is instant.
    On shutdown:
      • Dispose the SQLAlchemy engine connection pool.
    """
    logger.info("=== AI-CRM HCP Module starting up ===")

    # DB connectivity check
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("[startup] PostgreSQL connection verified.")
    except Exception as e:
        logger.error(f"[startup] PostgreSQL connection FAILED: {e}")
        # Don't crash — let the health endpoint report the issue

    # Pre-compile LangGraph agent (validates GROQ_API_KEY is set)
    try:
        from app.agent.graph import get_hcp_agent
        get_hcp_agent()
        logger.info("[startup] LangGraph agent compiled and ready.")
    except Exception as e:
        logger.warning(f"[startup] LangGraph agent pre-compile warning: {e}")

    yield   # Application running

    logger.info("=== AI-CRM HCP Module shutting down ===")
    engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-First CRM — HCP Interaction Module",
    description=(
        "REST API powering the HCP Interaction Logger. "
        "Includes a LangGraph agent (openai/gpt-oss-20b via Groq) with 5 tools: "
        "log_interaction, edit_interaction, search_hcp, suggest_followups, summarize_interaction."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────
# CORS — allow the React dev server
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.cors_origin,        # http://localhost:3000 (from .env)
        "https://ai-crm-hcp-module-puce.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",     # fallback if React dev server bumps port
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Health endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check — verifies API + DB connectivity",
)
def health_check():
    """Returns API status and PostgreSQL connectivity status."""
    db_status = "connected"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
        version="1.0.0",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mount routers
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(hcps.router)
app.include_router(interactions.router)
app.include_router(follow_ups.router)
app.include_router(chat.router)


# ─────────────────────────────────────────────────────────────────────────────
# Root redirect
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {
        "message": "AI-CRM HCP Module API",
        "docs": "/docs",
        "health": "/health",
    }
