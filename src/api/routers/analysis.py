"""Endpoints pour les analyses et signaux LLM."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.models.database import AnalysisReportORM, get_db
from src.models.schemas import AnalysisReport, PortfolioSummary

router = APIRouter(prefix="/analysis", tags=["Analyses & Signaux"])


@router.get(
    "/{ticker}",
    response_model=list[AnalysisReport],
    summary="Historique des analyses pour un ticker",
)
def get_analyses(
    ticker: str,
    limit: int = Query(default=30, le=100),
    db: Session = Depends(get_db),
) -> list[AnalysisReport]:
    """Retourne l'historique des rapports d'analyse pour un ticker."""
    rows = (
        db.query(AnalysisReportORM)
        .filter(AnalysisReportORM.ticker == ticker.upper())
        .order_by(AnalysisReportORM.analysis_date.desc())
        .limit(limit)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Aucune analyse trouvée pour {ticker}")
    return [AnalysisReport.model_validate(row) for row in rows]


@router.get(
    "/{ticker}/latest",
    response_model=AnalysisReport,
    summary="Dernière analyse pour un ticker",
)
def get_latest_analysis(ticker: str, db: Session = Depends(get_db)) -> AnalysisReport:
    """Retourne le rapport d'analyse le plus récent pour un ticker."""
    row = (
        db.query(AnalysisReportORM)
        .filter(AnalysisReportORM.ticker == ticker.upper())
        .order_by(AnalysisReportORM.analysis_date.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Aucune analyse trouvée pour {ticker}")
    return AnalysisReport.model_validate(row)


@router.get(
    "/portfolio/summary",
    response_model=PortfolioSummary,
    summary="Résumé du portefeuille complet",
)
def get_portfolio_summary(
    tickers: str = Query(..., description="Tickers séparés par des virgules (ex: AAPL,MSFT)"),
    analysis_date: Optional[date] = Query(None, description="Date d'analyse (défaut: aujourd'hui)"),
    db: Session = Depends(get_db),
) -> PortfolioSummary:
    """Retourne le résumé des signaux pour un portefeuille de tickers."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    target_date = analysis_date or date.today()

    reports = []
    for ticker in ticker_list:
        row = (
            db.query(AnalysisReportORM)
            .filter(
                AnalysisReportORM.ticker == ticker,
                AnalysisReportORM.analysis_date == target_date,
            )
            .first()
        )
        if row:
            reports.append(AnalysisReport.model_validate(row))

    from src.models.schemas import SentimentSignal

    bullish = sum(1 for r in reports if r.signal == SentimentSignal.BULLISH)
    neutral = sum(1 for r in reports if r.signal == SentimentSignal.NEUTRAL)
    bearish = sum(1 for r in reports if r.signal == SentimentSignal.BEARISH)

    return PortfolioSummary(
        tickers=ticker_list,
        analysis_date=target_date,
        bullish_count=bullish,
        neutral_count=neutral,
        bearish_count=bearish,
        reports=reports,
    )
