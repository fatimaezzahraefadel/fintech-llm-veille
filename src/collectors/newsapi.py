"""Collecteur d'articles de presse via NewsAPI."""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from typing import Optional

from loguru import logger
from newsapi import NewsApiClient
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.schemas import DataSource, NewsArticle


class NewsAPICollector:
    """Collecte les articles de presse filtrés par ticker via NewsAPI."""

    # Mapping ticker → termes de recherche enrichis
    TICKER_SEARCH_TERMS: dict[str, str] = {
        "AAPL": "Apple Inc stock",
        "MSFT": "Microsoft stock",
        "GOOGL": "Google Alphabet stock",
        "AMZN": "Amazon stock",
        "NVDA": "NVIDIA stock",
        "TSLA": "Tesla stock",
        "META": "Meta Facebook stock",
    }

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.client = NewsApiClient(api_key=api_key or settings.newsapi_key)

    @staticmethod
    def _compute_hash(title: str, url: str) -> str:
        """Calcule un hash SHA-256 pour la déduplication."""
        content = f"{title}|{url}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_search_query(self, ticker: str) -> str:
        """Retourne la requête de recherche optimisée pour un ticker."""
        return self.TICKER_SEARCH_TERMS.get(ticker.upper(), f"{ticker} stock earnings")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def fetch_articles(
        self,
        ticker: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        max_articles: int = 50,
        language: str = "en",
    ) -> list[NewsArticle]:
        """
        Récupère les articles de presse pour un ticker.

        Args:
            ticker: Symbole boursier.
            from_date: Date de début (défaut: hier).
            to_date: Date de fin (défaut: aujourd'hui).
            max_articles: Nombre maximum d'articles à retourner.
            language: Langue des articles ('en', 'fr').

        Returns:
            Liste de NewsArticle validés.
        """
        ticker = ticker.upper().strip()
        to_dt = to_date or date.today()
        from_dt = from_date or (to_dt - timedelta(days=7))

        query = self._get_search_query(ticker)
        logger.info(f"[NewsAPI] Collecte articles pour {ticker} (query: '{query}')")

        response = self.client.get_everything(
            q=query,
            from_param=from_dt.isoformat(),
            to=to_dt.isoformat(),
            language=language,
            sort_by="relevancy",
            page_size=min(max_articles, 100),
        )

        if response.get("status") != "ok":
            logger.error(f"[NewsAPI] Erreur API pour {ticker}: {response}")
            return []

        articles: list[NewsArticle] = []
        for raw in response.get("articles", []):
            try:
                published_at_str = raw.get("publishedAt", "")
                published_at = datetime.fromisoformat(
                    published_at_str.replace("Z", "+00:00")
                )

                title = raw.get("title") or ""
                url = raw.get("url") or ""

                if not title or not url:
                    continue

                article = NewsArticle(
                    ticker=ticker,
                    title=title[:500],
                    description=(raw.get("description") or "")[:2000],
                    content=(raw.get("content") or ""),
                    url=url,
                    source_name=raw.get("source", {}).get("name", "Unknown"),
                    published_at=published_at,
                    content_hash=self._compute_hash(title, url),
                    source=DataSource.NEWSAPI,
                )
                articles.append(article)
            except Exception as e:
                logger.warning(f"[NewsAPI] Article ignoré pour {ticker}: {e}")

        logger.success(f"[NewsAPI] {len(articles)} articles collectés pour {ticker}")
        return articles

    def fetch_multiple(
        self,
        tickers: list[str],
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict[str, list[NewsArticle]]:
        """Collecte les articles pour plusieurs tickers."""
        results: dict[str, list[NewsArticle]] = {}
        for ticker in tickers:
            try:
                results[ticker] = self.fetch_articles(ticker, from_date, to_date)
            except Exception as e:
                logger.error(f"[NewsAPI] Erreur pour {ticker}: {e}")
                results[ticker] = []
        return results
