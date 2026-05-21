"""Modèles SQLAlchemy et configuration de la base de données."""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.config import settings


# ─── Base & Engine ────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


def get_engine():
    """Crée et retourne le moteur SQLAlchemy."""
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=settings.environment == "development",
    )


def get_session_factory(engine=None):
    """Retourne une factory de sessions SQLAlchemy."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db():
    """Générateur de session pour FastAPI Depends."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crée toutes les tables si elles n'existent pas."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


# ─── Modèles ORM ──────────────────────────────────────────────────────────────


class StockPriceORM(Base):
    """Table des cours d'actions."""

    __tablename__ = "stock_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    adj_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_stock_ticker_date"),
        Index("ix_stock_ticker_date", "ticker", "date"),
    )


class NewsArticleORM(Base):
    """Table des articles de presse."""

    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="newsapi")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_news_ticker_published", "ticker", "published_at"),)


class AnalysisReportORM(Base):
    """Table des rapports d'analyse générés par le LLM."""

    __tablename__ = "analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    signal: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_factors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sources_used: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    raw_llm_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini-2.0-flash")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", "analysis_date", name="uq_analysis_ticker_date"),
        Index("ix_analysis_ticker_date", "ticker", "analysis_date"),
    )
