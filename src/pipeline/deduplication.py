"""Utilitaires de déduplication des données collectées."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import TypeVar

from loguru import logger

from src.models.schemas import NewsArticle, StockPrice

T = TypeVar("T")


def deduplicate_stock_prices(prices: list[StockPrice]) -> list[StockPrice]:
    """
    Déduplique une liste de cours en gardant le dernier par (ticker, date).

    Returns:
        Liste dédupliquée.
    """
    seen: dict[tuple[str, object], StockPrice] = {}
    for price in prices:
        key = (price.ticker, price.date)
        seen[key] = price  # Garde le dernier en cas de doublon

    result = list(seen.values())
    duplicates = len(prices) - len(result)
    if duplicates > 0:
        logger.debug(f"[Dedup] {duplicates} cours dupliqués supprimés")
    return result


def deduplicate_articles(articles: list[NewsArticle]) -> list[NewsArticle]:
    """
    Déduplique les articles par content_hash ou (title, url).

    Returns:
        Liste dédupliquée.
    """
    seen_hashes: set[str] = set()
    seen_titles: set[str] = set()
    result: list[NewsArticle] = []

    for article in articles:
        # Déduplication par hash
        if article.content_hash:
            if article.content_hash in seen_hashes:
                continue
            seen_hashes.add(article.content_hash)
        else:
            # Fallback: déduplication par titre normalisé
            title_key = article.title.lower().strip()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

        result.append(article)

    duplicates = len(articles) - len(result)
    if duplicates > 0:
        logger.debug(f"[Dedup] {duplicates} articles dupliqués supprimés")
    return result


def compute_content_hash(text: str) -> str:
    """Calcule un hash SHA-256 d'un texte pour la déduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def group_articles_by_ticker(articles: list[NewsArticle]) -> dict[str, list[NewsArticle]]:
    """Groupe les articles par ticker."""
    groups: dict[str, list[NewsArticle]] = defaultdict(list)
    for article in articles:
        groups[article.ticker].append(article)
    return dict(groups)


def group_prices_by_ticker(prices: list[StockPrice]) -> dict[str, list[StockPrice]]:
    """Groupe les cours par ticker."""
    groups: dict[str, list[StockPrice]] = defaultdict(list)
    for price in prices:
        groups[price.ticker].append(price)
    return dict(groups)
