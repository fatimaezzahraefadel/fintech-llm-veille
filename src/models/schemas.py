"""Schémas Pydantic pour la validation des données du pipeline."""

from __future__ import annotations

import datetime as dt
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Enums ────────────────────────────────────────────────────────────────────


class SentimentSignal(str, Enum):
    BULLISH = "haussier"
    NEUTRAL = "neutre"
    BEARISH = "baissier"


class DataSource(str, Enum):
    YAHOO_FINANCE = "yahoo_finance"
    NEWSAPI = "newsapi"
    SEC_EDGAR = "sec_edgar"
    ALPHA_VANTAGE = "alpha_vantage"
    REDDIT = "reddit"


# ─── Cours d'actions ──────────────────────────────────────────────────────────


class StockPrice(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    date: dt.date = Field(..., description="Date de la cotation")
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)
    adj_close: Optional[float] = Field(None, gt=0)

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    model_config = {"from_attributes": True}


class StockPriceCreate(StockPrice):
    pass


# ─── Articles de presse ───────────────────────────────────────────────────────


class NewsArticle(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    content: Optional[str] = Field(None)
    url: str = Field(...)
    source_name: str = Field(...)
    published_at: dt.datetime = Field(...)
    content_hash: Optional[str] = Field(None)
    source: DataSource = Field(default=DataSource.NEWSAPI)

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    model_config = {"from_attributes": True}


class NewsArticleCreate(NewsArticle):
    pass


# ─── Rapports d'analyse ───────────────────────────────────────────────────────


class AnalysisReport(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    analysis_date: dt.date = Field(...)
    signal: SentimentSignal = Field(...)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    summary: str = Field(..., min_length=10)
    key_factors: List[str] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)
    raw_llm_response: Optional[str] = Field(None)
    model_used: str = Field(default="gemini-2.0-flash")
    created_at: Optional[dt.datetime] = Field(None)

    @field_validator("ticker")
    @classmethod
    def ticker_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    model_config = {"from_attributes": True}


class AnalysisReportCreate(AnalysisReport):
    pass


# ─── Réponses API ─────────────────────────────────────────────────────────────


class PortfolioSummary(BaseModel):
    tickers: List[str]
    analysis_date: dt.date
    bullish_count: int
    neutral_count: int
    bearish_count: int
    reports: List[AnalysisReport]


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=5, max_length=1000)
    ticker: Optional[str] = Field(None)
    include_rag: bool = Field(default=True)


class AgentQueryResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    ticker: Optional[str] = None
    signal: Optional[SentimentSignal] = None
