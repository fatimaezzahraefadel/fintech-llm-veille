"""Endpoints pour les cours d'actions."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.models.database import StockPriceORM, get_db
from src.models.schemas import StockPrice

router = APIRouter(prefix="/prices", tags=["Cours d'actions"])


@router.get("/{ticker}", response_model=list[StockPrice], summary="Cours historiques d'un ticker")
def get_prices(
    ticker: str,
    start_date: Optional[date] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    limit: int = Query(default=100, le=500, description="Nombre maximum de résultats"),
    db: Session = Depends(get_db),
) -> list[StockPrice]:
    """Retourne les cours historiques pour un ticker donné."""
    query = db.query(StockPriceORM).filter(
        StockPriceORM.ticker == ticker.upper()
    )

    if start_date:
        query = query.filter(StockPriceORM.date >= start_date)
    if end_date:
        query = query.filter(StockPriceORM.date <= end_date)

    rows = query.order_by(StockPriceORM.date.desc()).limit(limit).all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Aucun cours trouvé pour {ticker}")

    return [StockPrice.model_validate(row) for row in rows]


@router.get(
    "/{ticker}/latest",
    response_model=StockPrice,
    summary="Dernier cours connu d'un ticker",
)
def get_latest_price(ticker: str, db: Session = Depends(get_db)) -> StockPrice:
    """Retourne le dernier cours enregistré pour un ticker."""
    row = (
        db.query(StockPriceORM)
        .filter(StockPriceORM.ticker == ticker.upper())
        .order_by(StockPriceORM.date.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Aucun cours trouvé pour {ticker}")
    return StockPrice.model_validate(row)
