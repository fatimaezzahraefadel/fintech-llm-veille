"""Tests unitaires pour les collecteurs de données."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.collectors.yahoo_finance import YahooFinanceCollector
from src.models.schemas import StockPrice


class TestYahooFinanceCollector:
    """Tests pour le collecteur Yahoo Finance."""

    def setup_method(self) -> None:
        self.collector = YahooFinanceCollector()

    def test_ticker_uppercase(self) -> None:
        """Le ticker doit être normalisé en majuscules."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            result = self.collector.fetch_historical("aapl")
            assert result == []

    def test_fetch_historical_returns_stock_prices(self) -> None:
        """fetch_historical doit retourner une liste de StockPrice."""
        mock_df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
                "Open": [185.0, 186.0],
                "High": [187.0, 188.0],
                "Low": [184.0, 185.0],
                "Close": [186.5, 187.0],
                "Volume": [50_000_000, 48_000_000],
                "Adj Close": [186.5, 187.0],
            }
        )

        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = mock_df
            result = self.collector.fetch_historical("AAPL")

        assert len(result) == 2
        assert all(isinstance(p, StockPrice) for p in result)
        assert result[0].ticker == "AAPL"
        assert result[0].close == pytest.approx(186.5)

    def test_fetch_historical_empty_returns_empty_list(self) -> None:
        """Un DataFrame vide doit retourner une liste vide."""
        with patch("yfinance.Ticker") as mock_ticker:
            mock_ticker.return_value.history.return_value = pd.DataFrame()
            result = self.collector.fetch_historical("UNKNOWN")
        assert result == []

    def test_fetch_multiple_handles_errors(self) -> None:
        """fetch_multiple doit gérer les erreurs par ticker sans planter."""
        with patch.object(
            self.collector,
            "fetch_historical",
            side_effect=Exception("API Error"),
        ):
            result = self.collector.fetch_multiple(["AAPL", "MSFT"])

        assert "AAPL" in result
        assert "MSFT" in result
        assert result["AAPL"] == []
        assert result["MSFT"] == []
