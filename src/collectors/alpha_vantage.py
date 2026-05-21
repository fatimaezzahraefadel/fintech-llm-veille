"""Collecteur de données fondamentales via Alpha Vantage."""

from __future__ import annotations

from typing import Any, Optional

import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"


class AlphaVantageCollector:
    """Collecte les données fondamentales et indicateurs techniques via Alpha Vantage."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.alpha_vantage_key

    def _get(self, params: dict[str, str]) -> dict[str, Any]:
        """Effectue une requête GET vers l'API Alpha Vantage."""
        params["apikey"] = self.api_key
        with httpx.Client(timeout=30) as client:
            resp = client.get(ALPHA_VANTAGE_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        if "Note" in data:
            logger.warning("[AlphaVantage] Rate limit atteint. Attendre 1 minute.")
        if "Error Message" in data:
            logger.error(f"[AlphaVantage] Erreur API: {data['Error Message']}")
            return {}
        return data

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def get_company_overview(self, ticker: str) -> dict[str, Any]:
        """
        Retourne les données fondamentales d'une entreprise.

        Inclut: secteur, capitalisation, P/E, EPS, dividendes, etc.
        """
        logger.info(f"[AlphaVantage] Company overview pour {ticker}")
        return self._get({"function": "OVERVIEW", "symbol": ticker.upper()})

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def get_rsi(self, ticker: str, interval: str = "daily", time_period: int = 14) -> dict:
        """Retourne le RSI (Relative Strength Index) pour un ticker."""
        logger.info(f"[AlphaVantage] RSI pour {ticker}")
        return self._get(
            {
                "function": "RSI",
                "symbol": ticker.upper(),
                "interval": interval,
                "time_period": str(time_period),
                "series_type": "close",
            }
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def get_macd(self, ticker: str, interval: str = "daily") -> dict:
        """Retourne le MACD pour un ticker."""
        logger.info(f"[AlphaVantage] MACD pour {ticker}")
        return self._get(
            {
                "function": "MACD",
                "symbol": ticker.upper(),
                "interval": interval,
                "series_type": "close",
            }
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30), reraise=True)
    def get_earnings(self, ticker: str) -> dict:
        """Retourne l'historique des bénéfices trimestriels."""
        logger.info(f"[AlphaVantage] Earnings pour {ticker}")
        return self._get({"function": "EARNINGS", "symbol": ticker.upper()})

    def get_fundamentals_summary(self, ticker: str) -> dict[str, Any]:
        """
        Retourne un résumé des indicateurs fondamentaux clés.

        Combine company overview + RSI pour une vue rapide.
        """
        overview = self.get_company_overview(ticker)
        rsi_data = self.get_rsi(ticker)

        # Extraire le RSI le plus récent
        latest_rsi: Optional[float] = None
        rsi_series = rsi_data.get("Technical Analysis: RSI", {})
        if rsi_series:
            latest_date = max(rsi_series.keys())
            latest_rsi = float(rsi_series[latest_date].get("RSI", 0))

        return {
            "ticker": ticker.upper(),
            "sector": overview.get("Sector", "N/A"),
            "industry": overview.get("Industry", "N/A"),
            "market_cap": overview.get("MarketCapitalization", "N/A"),
            "pe_ratio": overview.get("PERatio", "N/A"),
            "eps": overview.get("EPS", "N/A"),
            "dividend_yield": overview.get("DividendYield", "N/A"),
            "52_week_high": overview.get("52WeekHigh", "N/A"),
            "52_week_low": overview.get("52WeekLow", "N/A"),
            "analyst_target_price": overview.get("AnalystTargetPrice", "N/A"),
            "rsi_14": latest_rsi,
            "description": overview.get("Description", ""),
        }
