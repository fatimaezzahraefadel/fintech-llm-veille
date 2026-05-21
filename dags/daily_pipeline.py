"""DAG Airflow — Pipeline de collecte et d'analyse quotidienne."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Ajouter le répertoire src au path
sys.path.insert(0, "/opt/airflow")

# ─── Configuration du DAG ─────────────────────────────────────────────────────

DEFAULT_ARGS = {
    "owner": "fintech-veille",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

TICKERS = [t.strip() for t in os.getenv("WATCHED_TICKERS", "AAPL,MSFT,GOOGL,AMZN,NVDA").split(",")]


# ─── Fonctions des tâches ─────────────────────────────────────────────────────


def collect_stock_prices(**context) -> None:
    """Collecte les cours d'actions pour tous les tickers."""
    from src.collectors.yahoo_finance import YahooFinanceCollector
    from src.models.database import get_engine, get_session_factory
    from src.pipeline.deduplication import deduplicate_stock_prices
    from src.pipeline.ingestion import upsert_stock_prices

    collector = YahooFinanceCollector(default_period_days=7)
    engine = get_engine()
    SessionLocal = get_session_factory(engine)

    total_inserted = 0
    with SessionLocal() as db:
        for ticker in TICKERS:
            try:
                prices = collector.fetch_historical(ticker)
                prices = deduplicate_stock_prices(prices)
                inserted = upsert_stock_prices(db, prices)
                total_inserted += inserted
            except Exception as e:
                from loguru import logger
                logger.error(f"[DAG] Erreur collecte prix {ticker}: {e}")

    context["ti"].xcom_push(key="prices_inserted", value=total_inserted)


def collect_news_articles(**context) -> None:
    """Collecte les articles de presse pour tous les tickers."""
    from src.collectors.newsapi import NewsAPICollector
    from src.models.database import get_engine, get_session_factory
    from src.pipeline.deduplication import deduplicate_articles
    from src.pipeline.ingestion import upsert_news_articles
    from src.pipeline.cleaner import clean_article_text

    collector = NewsAPICollector()
    engine = get_engine()
    SessionLocal = get_session_factory(engine)

    total_inserted = 0
    with SessionLocal() as db:
        for ticker in TICKERS:
            try:
                articles = collector.fetch_articles(ticker, max_articles=30)
                # Nettoyer le contenu
                for article in articles:
                    if article.content:
                        object.__setattr__(
                            article, "content", clean_article_text(article.content)
                        )
                articles = deduplicate_articles(articles)
                inserted = upsert_news_articles(db, articles)
                total_inserted += inserted
            except Exception as e:
                from loguru import logger
                logger.error(f"[DAG] Erreur collecte news {ticker}: {e}")

    context["ti"].xcom_push(key="articles_inserted", value=total_inserted)


def index_new_articles(**context) -> None:
    """Indexe les nouveaux articles dans ChromaDB."""
    from datetime import date, timedelta
    from src.agent.chromadb_index import ChromaDBIndex
    from src.models.database import get_engine, get_session_factory, NewsArticleORM

    engine = get_engine()
    SessionLocal = get_session_factory(engine)
    index = ChromaDBIndex()

    yesterday = date.today() - timedelta(days=1)
    total_chunks = 0

    with SessionLocal() as db:
        recent_articles = (
            db.query(NewsArticleORM)
            .filter(NewsArticleORM.published_at >= yesterday)
            .all()
        )

        articles_dicts = [
            {
                "ticker": a.ticker,
                "title": a.title,
                "content": a.content or a.description or "",
                "published_at": str(a.published_at),
                "url": a.url,
                "content_hash": a.content_hash,
            }
            for a in recent_articles
            if a.content or a.description
        ]

        total_chunks = index.index_news_articles(articles_dicts)

    context["ti"].xcom_push(key="chunks_indexed", value=total_chunks)


def run_llm_analysis(**context) -> None:
    """Lance l'analyse LLM pour tous les tickers."""
    from datetime import date
    from src.agent.signal_engine import SignalEngine
    from src.models.database import get_engine, get_session_factory
    from src.pipeline.ingestion import (
        get_recent_articles,
        get_latest_prices,
        upsert_analysis_report,
    )

    engine = get_engine()
    SessionLocal = get_session_factory(engine)
    signal_engine = SignalEngine()
    today = date.today()

    reports_generated = 0
    with SessionLocal() as db:
        for ticker in TICKERS:
            try:
                # Récupérer les données depuis la BDD
                prices = get_latest_prices(db, ticker, limit=30)
                articles = get_recent_articles(db, ticker, limit=15)

                prices_dicts = [
                    {
                        "date": str(p.date),
                        "open": p.open,
                        "close": p.close,
                        "volume": p.volume,
                    }
                    for p in prices
                ]
                articles_dicts = [
                    {
                        "title": a.title,
                        "description": a.description or "",
                        "published_at": str(a.published_at),
                        "source_name": a.source_name,
                    }
                    for a in articles
                ]

                report = signal_engine.analyze_ticker(
                    ticker=ticker,
                    prices=prices_dicts,
                    articles=articles_dicts,
                    analysis_date=today,
                )
                upsert_analysis_report(db, report)
                reports_generated += 1

            except Exception as e:
                from loguru import logger
                logger.error(f"[DAG] Erreur analyse LLM {ticker}: {e}")

    context["ti"].xcom_push(key="reports_generated", value=reports_generated)


def log_pipeline_summary(**context) -> None:
    """Log un résumé du pipeline."""
    ti = context["ti"]
    prices = ti.xcom_pull(task_ids="collect_stock_prices", key="prices_inserted") or 0
    articles = ti.xcom_pull(task_ids="collect_news_articles", key="articles_inserted") or 0
    chunks = ti.xcom_pull(task_ids="index_new_articles", key="chunks_indexed") or 0
    reports = ti.xcom_pull(task_ids="run_llm_analysis", key="reports_generated") or 0

    from loguru import logger
    logger.info(
        f"[DAG] Pipeline terminé — "
        f"Cours: {prices} | Articles: {articles} | "
        f"Chunks indexés: {chunks} | Rapports: {reports}"
    )


# ─── Définition du DAG ────────────────────────────────────────────────────────

with DAG(
    dag_id="daily_financial_pipeline",
    description="Pipeline quotidien de collecte et d'analyse financière",
    default_args=DEFAULT_ARGS,
    schedule="0 7 * * 1-5",  # 7h00 du lundi au vendredi
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["fintech", "llm", "finance"],
    max_active_runs=1,
) as dag:

    t1_prices = PythonOperator(
        task_id="collect_stock_prices",
        python_callable=collect_stock_prices,
    )

    t2_news = PythonOperator(
        task_id="collect_news_articles",
        python_callable=collect_news_articles,
    )

    t3_index = PythonOperator(
        task_id="index_new_articles",
        python_callable=index_new_articles,
    )

    t4_analysis = PythonOperator(
        task_id="run_llm_analysis",
        python_callable=run_llm_analysis,
    )

    t5_summary = PythonOperator(
        task_id="log_pipeline_summary",
        python_callable=log_pipeline_summary,
    )

    # Dépendances: collecte en parallèle → indexation → analyse → résumé
    [t1_prices, t2_news] >> t3_index >> t4_analysis >> t5_summary
