"""Tests unitaires pour l'agent LLM et le moteur de signaux."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.models.schemas import AnalysisReport, SentimentSignal


class TestSignalEngine:
    """Tests pour le moteur de génération de signaux."""

    def _make_engine(self):
        """Crée un SignalEngine avec des mocks."""
        with patch("src.agent.signal_engine.ChatGoogleGenerativeAI"), \
             patch("src.agent.signal_engine.ChromaDBIndex"):
            from src.agent.signal_engine import SignalEngine
            engine = SignalEngine()
            return engine

    def test_format_price_data_empty(self) -> None:
        engine = self._make_engine()
        result = engine._format_price_data([])
        assert "Aucune" in result

    def test_format_price_data_with_data(self) -> None:
        engine = self._make_engine()
        prices = [
            {"date": "2024-01-02", "open": 185.0, "close": 186.5, "volume": 50_000_000},
        ]
        result = engine._format_price_data(prices)
        assert "2024-01-02" in result
        assert "185" in result

    def test_format_news_data_empty(self) -> None:
        engine = self._make_engine()
        result = engine._format_news_data([])
        assert "Aucun" in result

    def test_analyze_ticker_returns_report_on_valid_json(self) -> None:
        """analyze_ticker doit retourner un AnalysisReport valide."""
        engine = self._make_engine()

        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "signal": "haussier",
                "confidence_score": 0.82,
                "summary": "Apple affiche de solides résultats trimestriels.",
                "key_factors": ["Croissance iPhone", "Services en hausse"],
                "sources_used": ["NewsAPI", "SEC EDGAR"],
            }
        )

        engine.chain = MagicMock(return_value=mock_response)
        engine.chroma_index.similarity_search = MagicMock(return_value=[])

        report = engine.analyze_ticker(
            ticker="AAPL",
            prices=[{"date": "2024-01-02", "open": 185.0, "close": 186.5, "volume": 50_000_000}],
            articles=[{"title": "Apple Q1 results", "description": "Strong", "published_at": "2024-01-25", "source_name": "Reuters"}],
        )

        assert isinstance(report, AnalysisReport)
        assert report.ticker == "AAPL"
        assert report.signal == SentimentSignal.BULLISH
        assert report.confidence_score == pytest.approx(0.82)

    def test_analyze_ticker_fallback_on_invalid_json(self) -> None:
        """analyze_ticker doit retourner un rapport neutre si le JSON est invalide."""
        engine = self._make_engine()

        mock_response = MagicMock()
        mock_response.content = "Ceci n'est pas du JSON valide"

        engine.chain = MagicMock(return_value=mock_response)
        engine.chroma_index.similarity_search = MagicMock(return_value=[])

        report = engine.analyze_ticker(
            ticker="AAPL",
            prices=[],
            articles=[],
        )

        assert report.signal == SentimentSignal.NEUTRAL
        assert report.confidence_score == 0.0


class TestSchemas:
    """Tests de validation des schémas Pydantic."""

    def test_stock_price_ticker_uppercase(self) -> None:
        from src.models.schemas import StockPrice
        price = StockPrice(
            ticker="aapl",
            date=date(2024, 1, 2),
            open=185.0,
            high=187.0,
            low=184.0,
            close=186.5,
            volume=50_000_000,
        )
        assert price.ticker == "AAPL"

    def test_analysis_report_signal_validation(self) -> None:
        from src.models.schemas import AnalysisReport
        report = AnalysisReport(
            ticker="MSFT",
            analysis_date=date(2024, 1, 15),
            signal=SentimentSignal.BULLISH,
            confidence_score=0.75,
            summary="Microsoft affiche une forte croissance cloud.",
            key_factors=["Azure +28%", "Copilot adoption"],
            sources_used=["NewsAPI"],
        )
        assert report.signal == SentimentSignal.BULLISH
        assert report.confidence_score == pytest.approx(0.75)

    def test_analysis_report_confidence_bounds(self) -> None:
        from pydantic import ValidationError
        from src.models.schemas import AnalysisReport
        with pytest.raises(ValidationError):
            AnalysisReport(
                ticker="AAPL",
                analysis_date=date(2024, 1, 15),
                signal=SentimentSignal.NEUTRAL,
                confidence_score=1.5,  # Invalide: > 1.0
                summary="Test",
            )
