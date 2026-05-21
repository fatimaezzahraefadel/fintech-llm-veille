"""Point d'entrée de l'API FastAPI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routers import agent, analysis, prices
from src.config import settings
from src.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gestion du cycle de vie de l'application."""
    logger.info("🚀 Démarrage de la plateforme de veille financière...")
    # Initialiser la base de données
    try:
        init_db()
        logger.success("✅ Base de données initialisée")
    except Exception as e:
        logger.error(f"❌ Erreur initialisation BDD: {e}")

    yield

    logger.info("🛑 Arrêt de l'application")


app = FastAPI(
    title="Plateforme de Veille Financière LLM",
    description=(
        "API REST pour l'agrégation de données financières et la génération "
        "d'analyses de sentiment via LLM (Gemini 1.5 Pro + RAG)."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else ["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(prices.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Système"])
def health_check() -> dict:
    """Vérifie que l'API est opérationnelle."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "model": settings.gemini_model,
        "tickers": settings.tickers_list,
    }


@app.get("/", tags=["Système"])
def root() -> dict:
    """Endpoint racine avec liens vers la documentation."""
    return {
        "message": "Plateforme de Veille Financière LLM",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }
