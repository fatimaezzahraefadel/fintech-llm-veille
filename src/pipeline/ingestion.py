"""Fonctions d'ingestion des données dans PostgreSQL."""

from __future__ import annotations

from typing import Sequence

from loguru import logger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.models.database import AnalysisReportORM, NewsArticleORM, StockPriceORM
from src.models.schemas import AnalysisReport, NewsArticle, StockPrice


# ─── Stock Prices ─────────────────────────────────────────────────────────────


def upsert_stock_prices(db: Session, prices: Sequence[StockPrice]) -> int:
    """
    Insère ou met à jour les cours d'actions (ON CONFLICT DO NOTHING).

    Returns:
        Nombre d'enregistrements insérés.
    """
    if not prices:
        return 0

    rows = [
        {
            "ticker": p.ticker,
            "date": p.date,
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "close": p.close,
            "volume": p.volume,
            "adj_close": p.adj_close,
        }
        for p in prices
    ]

    stmt = insert(StockPriceORM).values(rows)
    stmt = stmt.on_conflict_do_nothing(constraint="uq_stock_ticker_date")
    result = db.execute(stmt)
    db.commit()

    inserted = result.rowcount
    logger.info(f"[Ingestion] {inserted}/{len(rows)} cours insérés")
    return inserted


# ─── News Articles ────────────────────────────────────────────────────────────


def upsert_news_articles(db: Session, articles: Sequence[NewsArticle]) -> int:
    """
    Insère les articles en ignorant les doublons (déduplication par content_hash).

    Returns:
        Nombre d'articles insérés.
    """
    if not articles:
        return 0

    rows = [
        {
            "ticker": a.ticker,
            "title": a.title,
            "description": a.description,
            "content": a.content,
            "url": str(a.url),
            "source_name": a.source_name,
            "published_at": a.published_at,
            "content_hash": a.content_hash,
            "source": a.source.value if a.source else "newsapi",
        }
        for a in articles
    ]

    stmt = insert(NewsArticleORM).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["content_hash"])
    result = db.execute(stmt)
    db.commit()

    inserted = result.rowcount
    logger.info(f"[Ingestion] {inserted}/{len(rows)} articles insérés")
    return inserted


# ─── Analysis Reports ─────────────────────────────────────────────────────────


def upsert_analysis_report(db: Session, report: AnalysisReport) -> bool:
    """
    Insère ou met à jour un rapport d'analyse (ON CONFLICT UPDATE).

    Returns:
        True si inséré, False si mis à jour.
    """
    row = {
        "ticker": report.ticker,
        "analysis_date": report.analysis_date,
        "signal": report.signal.value,
        "confidence_score": report.confidence_score,
        "summary": report.summary,
        "key_factors": report.key_factors,
        "sources_used": report.sources_used,
        "raw_llm_response": report.raw_llm_response,
        "model_used": report.model_used,
    }

    stmt = insert(AnalysisReportORM).values([row])
    stmt = stmt.on_conflict_do_update(
        constraint="uq_analysis_ticker_date",
        set_={
            "signal": stmt.excluded.signal,
            "confidence_score": stmt.excluded.confidence_score,
            "summary": stmt.excluded.summary,
            "key_factors": stmt.excluded.key_factors,
            "sources_used": stmt.excluded.sources_used,
            "raw_llm_response": stmt.excluded.raw_llm_response,
        },
    )
    result = db.execute(stmt)
    db.commit()

    inserted = result.rowcount == 1
    action = "inséré" if inserted else "mis à jour"
    logger.info(f"[Ingestion] Rapport {report.ticker} ({report.analysis_date}) {action}")
    return inserted


def get_recent_articles(
    db: Session, ticker: str, limit: int = 20
) -> list[NewsArticleORM]:
    """Retourne les articles les plus récents pour un ticker."""
    return (
        db.query(NewsArticleORM)
        .filter(NewsArticleORM.ticker == ticker)
        .order_by(NewsArticleORM.published_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_prices(
    db: Session, ticker: str, limit: int = 30
) -> list[StockPriceORM]:
    """Retourne les derniers cours pour un ticker."""
    return (
        db.query(StockPriceORM)
        .filter(StockPriceORM.ticker == ticker)
        .order_by(StockPriceORM.date.desc())
        .limit(limit)
        .all()
    )


def get_latest_report(
    db: Session, ticker: str
) -> AnalysisReportORM | None:
    """Retourne le rapport d'analyse le plus récent pour un ticker."""
    return (
        db.query(AnalysisReportORM)
        .filter(AnalysisReportORM.ticker == ticker)
        .order_by(AnalysisReportORM.analysis_date.desc())
        .first()
    )
