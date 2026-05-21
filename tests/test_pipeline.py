"""Tests unitaires pour le pipeline ETL."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from src.models.schemas import DataSource, NewsArticle, StockPrice
from src.pipeline.cleaner import (
    clean_article_text,
    clean_pdf_text,
    normalize_whitespace,
    strip_html,
    truncate_text,
)
from src.pipeline.deduplication import (
    deduplicate_articles,
    deduplicate_stock_prices,
)


# ─── Tests Cleaner ────────────────────────────────────────────────────────────


class TestCleaner:
    def test_strip_html_removes_tags(self) -> None:
        html = "<p>Hello <b>World</b></p>"
        assert "Hello" in strip_html(html)
        assert "<p>" not in strip_html(html)
        assert "<b>" not in strip_html(html)

    def test_strip_html_empty_string(self) -> None:
        assert strip_html("") == ""

    def test_normalize_whitespace(self) -> None:
        text = "Hello   World\n\nFoo"
        result = normalize_whitespace(text)
        assert "  " not in result
        assert result == "Hello World Foo"

    def test_clean_article_text_pipeline(self) -> None:
        raw = "<p>Apple Inc. reported <b>strong earnings</b>.\n\n© 2024 Reuters</p>"
        result = clean_article_text(raw)
        assert "<p>" not in result
        assert "Apple Inc." in result

    def test_truncate_text_respects_limit(self) -> None:
        text = "word " * 1000  # 5000 chars
        result = truncate_text(text, max_chars=100)
        assert len(result) <= 110  # Tolérance pour "..."
        assert result.endswith("...")

    def test_truncate_text_short_text_unchanged(self) -> None:
        text = "Short text"
        assert truncate_text(text, max_chars=100) == text

    def test_clean_pdf_text_removes_page_numbers(self) -> None:
        text = "Introduction\n\n42\n\nContent here"
        result = clean_pdf_text(text)
        assert "Introduction" in result
        assert "Content here" in result


# ─── Tests Deduplication ──────────────────────────────────────────────────────


def _make_price(ticker: str, day: int) -> StockPrice:
    return StockPrice(
        ticker=ticker,
        date=date(2024, 1, day),
        open=100.0,
        high=105.0,
        low=99.0,
        close=103.0,
        volume=1_000_000,
    )


def _make_article(ticker: str, title: str, url: str) -> NewsArticle:
    return NewsArticle(
        ticker=ticker,
        title=title,
        url=url,
        source_name="Reuters",
        published_at=datetime(2024, 1, 15, 10, 0),
        content_hash=None,
        source=DataSource.NEWSAPI,
    )


class TestDeduplication:
    def test_deduplicate_stock_prices_removes_duplicates(self) -> None:
        prices = [
            _make_price("AAPL", 2),
            _make_price("AAPL", 2),  # Doublon
            _make_price("AAPL", 3),
        ]
        result = deduplicate_stock_prices(prices)
        assert len(result) == 2

    def test_deduplicate_stock_prices_different_tickers(self) -> None:
        prices = [_make_price("AAPL", 2), _make_price("MSFT", 2)]
        result = deduplicate_stock_prices(prices)
        assert len(result) == 2

    def test_deduplicate_articles_by_title(self) -> None:
        articles = [
            _make_article("AAPL", "Apple reports earnings", "https://a.com/1"),
            _make_article("AAPL", "Apple reports earnings", "https://a.com/2"),  # Même titre
            _make_article("AAPL", "Apple launches new product", "https://a.com/3"),
        ]
        result = deduplicate_articles(articles)
        assert len(result) == 2

    def test_deduplicate_articles_empty_list(self) -> None:
        assert deduplicate_articles([]) == []
