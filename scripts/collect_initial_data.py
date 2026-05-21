"""
Script de collecte initiale des données.
Lance une collecte complète : cours + articles pour tous les tickers configurés.
"""

import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, "/app")

from loguru import logger
from datetime import date, timedelta

from src.config import settings
from src.collectors.yahoo_finance import YahooFinanceCollector
from src.collectors.newsapi import NewsAPICollector
from src.models.database import get_engine, get_session_factory, init_db
from src.pipeline.deduplication import deduplicate_stock_prices, deduplicate_articles
from src.pipeline.ingestion import upsert_stock_prices, upsert_news_articles

def main():
    logger.info("=" * 60)
    logger.info("🚀 COLLECTE INITIALE DES DONNÉES")
    logger.info("=" * 60)
    logger.info(f"Tickers : {settings.tickers_list}")

    # Init BDD
    init_db()
    engine = get_engine()
    SessionLocal = get_session_factory(engine)

    # ── 1. Cours Yahoo Finance (90 derniers jours) ──────────────────
    logger.info("\n📈 Étape 1 : Collecte des cours Yahoo Finance...")
    yf_collector = YahooFinanceCollector(default_period_days=90)
    total_prices = 0

    with SessionLocal() as db:
        for ticker in settings.tickers_list:
            try:
                prices = yf_collector.fetch_historical(ticker)
                prices = deduplicate_stock_prices(prices)
                inserted = upsert_stock_prices(db, prices)
                total_prices += inserted
                logger.success(f"  ✅ {ticker} : {len(prices)} cours collectés, {inserted} insérés")
            except Exception as e:
                logger.error(f"  ❌ {ticker} : {e}")

    logger.info(f"\n  Total cours insérés : {total_prices}")

    # ── 2. Articles NewsAPI (7 derniers jours) ───────────────────────
    logger.info("\n📰 Étape 2 : Collecte des articles NewsAPI...")
    news_collector = NewsAPICollector()
    total_articles = 0

    with SessionLocal() as db:
        for ticker in settings.tickers_list:
            try:
                articles = news_collector.fetch_articles(
                    ticker,
                    from_date=date.today() - timedelta(days=7),
                    max_articles=20,
                )
                articles = deduplicate_articles(articles)
                inserted = upsert_news_articles(db, articles)
                total_articles += inserted
                logger.success(f"  ✅ {ticker} : {len(articles)} articles collectés, {inserted} insérés")
            except Exception as e:
                logger.error(f"  ❌ {ticker} : {e}")

    logger.info(f"\n  Total articles insérés : {total_articles}")

    # ── Résumé ───────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("✅ COLLECTE TERMINÉE")
    logger.info(f"   Cours    : {total_prices}")
    logger.info(f"   Articles : {total_articles}")
    logger.info("=" * 60)
    logger.info("\n👉 Prochaine étape : lancer l'analyse LLM")
    logger.info("   python scripts/run_llm_analysis.py")

if __name__ == "__main__":
    main()
