"""Collecteur de données boursières via yfinance."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.schemas import StockPrice


class YahooFinanceCollector:
    """Collecte les cours historiques et temps réel via Yahoo Finance."""

    def __init__(self, default_period_days: int = 365) -> None:
        self.default_period_days = default_period_days

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def fetch_historical(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[StockPrice]:
        """
        Récupère l'historique des cours pour un ticker.

        Args:
            ticker: Symbole boursier (ex: 'AAPL').
            start_date: Date de début (défaut: aujourd'hui - default_period_days).
            end_date: Date de fin (défaut: aujourd'hui).

        Returns:
            Liste de StockPrice validés par Pydantic.
        """
        ticker = ticker.upper().strip()
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=self.default_period_days))

        logger.info(f"[YahooFinance] Collecte {ticker} du {start} au {end}")

        yf_ticker = yf.Ticker(ticker)
        df: pd.DataFrame = yf_ticker.history(
            start=start.isoformat(),
            end=end.isoformat(),
            auto_adjust=False,
        )

        if df.empty:
            logger.warning(f"[YahooFinance] Aucune donnée pour {ticker}")
            return []

        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]

        prices: list[StockPrice] = []
        for _, row in df.iterrows():
            try:
                price = StockPrice(
                    ticker=ticker,
                    date=row["date"].date() if hasattr(row["date"], "date") else row["date"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                    adj_close=float(row.get("adj_close", row["close"])),
                )
                prices.append(price)
            except Exception as e:
                logger.warning(f"[YahooFinance] Ligne ignorée pour {ticker}: {e}")

        logger.success(f"[YahooFinance] {len(prices)} enregistrements collectés pour {ticker}")
        return prices

    def fetch_multiple(
        self,
        tickers: list[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict[str, list[StockPrice]]:
        """
        Collecte les cours pour plusieurs tickers.

        Returns:
            Dictionnaire {ticker: [StockPrice, ...]}.
        """
        results: dict[str, list[StockPrice]] = {}
        for ticker in tickers:
            try:
                results[ticker] = self.fetch_historical(ticker, start_date, end_date)
            except Exception as e:
                logger.error(f"[YahooFinance] Erreur pour {ticker}: {e}")
                results[ticker] = []
        return results

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Retourne le dernier prix connu pour un ticker."""
        try:
            yf_ticker = yf.Ticker(ticker.upper())
            info = yf_ticker.fast_info
            return float(info.last_price)
        except Exception as e:
            logger.error(f"[YahooFinance] Impossible de récupérer le prix de {ticker}: {e}")
            return None

    def get_ticker_info(self, ticker: str) -> dict:
        """Retourne les informations générales d'un ticker (secteur, capitalisation, etc.)."""
        try:
            yf_ticker = yf.Ticker(ticker.upper())
            return yf_ticker.info or {}
        except Exception as e:
            logger.error(f"[YahooFinance] Impossible de récupérer les infos de {ticker}: {e}")
            return {}
