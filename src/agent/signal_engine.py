"""Moteur de génération de signaux financiers via LangChain + Gemini."""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

from src.agent.chromadb_index import ChromaDBIndex
from src.agent.prompts import PORTFOLIO_SUMMARY_PROMPT, SENTIMENT_ANALYSIS_PROMPT
from src.config import settings
from src.models.schemas import AnalysisReport, SentimentSignal


class SignalEngine:
    """
    Génère des signaux de sentiment financier via un pipeline RAG + Gemini.

    Combine:
    - Données de prix (PostgreSQL)
    - Articles de presse récents
    - Contexte RAG (rapports SEC, documents indexés)
    - Indicateurs fondamentaux (Alpha Vantage)
    """

    def __init__(
        self,
        chroma_index: Optional[ChromaDBIndex] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
    ) -> None:
        self.llm = ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            temperature=temperature,
            google_api_key=settings.gemini_api_key,
            convert_system_message_to_human=True,
        )
        self.chroma_index = chroma_index or ChromaDBIndex()
        self.chain = SENTIMENT_ANALYSIS_PROMPT | self.llm

    def _format_price_data(self, prices: list[dict]) -> str:
        """Formate les données de prix pour le prompt."""
        if not prices:
            return "Aucune donnée de prix disponible."

        lines = ["Date | Ouverture | Clôture | Volume | Variation"]
        lines.append("-" * 55)
        for p in prices[:20]:
            variation = ""
            if p.get("open") and p.get("close"):
                pct = ((p["close"] - p["open"]) / p["open"]) * 100
                variation = f"{pct:+.2f}%"
            lines.append(
                f"{p.get('date', 'N/A')} | "
                f"{p.get('open', 0):.2f} | "
                f"{p.get('close', 0):.2f} | "
                f"{p.get('volume', 0):,} | "
                f"{variation}"
            )
        return "\n".join(lines)

    def _format_news_data(self, articles: list[dict]) -> str:
        """Formate les articles de presse pour le prompt."""
        if not articles:
            return "Aucun article disponible."

        parts = []
        for i, article in enumerate(articles[:10], 1):
            parts.append(
                f"{i}. [{article.get('published_at', 'N/A')}] "
                f"**{article.get('title', 'Sans titre')}** "
                f"({article.get('source_name', 'Source inconnue')})\n"
                f"   {article.get('description', '')[:200]}"
            )
        return "\n\n".join(parts)

    def _get_rag_context(self, ticker: str, analysis_date: date) -> str:
        """Récupère le contexte RAG pertinent depuis ChromaDB."""
        query = (
            f"financial performance earnings revenue outlook {ticker} "
            f"{analysis_date.year} quarterly results"
        )
        docs = self.chroma_index.similarity_search(query, ticker=ticker, k=5)

        if not docs:
            return "Aucun document indexé disponible pour ce ticker."

        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("type", "document")
            date_str = doc.metadata.get("filing_date", doc.metadata.get("published_at", "N/A"))
            parts.append(f"[Source {i} - {source} ({date_str})]:\n{doc.page_content[:500]}")

        return "\n\n---\n\n".join(parts)

    def analyze_ticker(
        self,
        ticker: str,
        prices: list[dict],
        articles: list[dict],
        fundamentals: Optional[dict] = None,
        analysis_date: Optional[date] = None,
    ) -> AnalysisReport:
        """
        Génère un rapport d'analyse complet pour un ticker.

        Args:
            ticker: Symbole boursier.
            prices: Liste de dicts de cours (date, open, close, volume).
            articles: Liste de dicts d'articles (title, description, published_at).
            fundamentals: Données fondamentales Alpha Vantage (optionnel).
            analysis_date: Date d'analyse (défaut: aujourd'hui).

        Returns:
            AnalysisReport validé par Pydantic.
        """
        analysis_date = analysis_date or date.today()
        ticker = ticker.upper()

        logger.info(f"[SignalEngine] Analyse de {ticker} pour le {analysis_date}")

        price_data = self._format_price_data(prices)
        news_data = self._format_news_data(articles)
        rag_context = self._get_rag_context(ticker, analysis_date)
        fundamentals_str = (
            json.dumps(fundamentals, indent=2, ensure_ascii=False)
            if fundamentals
            else "Données fondamentales non disponibles."
        )

        response = self.chain.invoke(
            {
                "ticker": ticker,
                "analysis_date": analysis_date.isoformat(),
                "price_data": price_data,
                "news_data": news_data,
                "rag_context": rag_context,
                "fundamentals": fundamentals_str,
            }
        )

        raw_response = response.content
        logger.debug(f"[SignalEngine] Réponse Gemini brute: {raw_response[:200]}...")

        try:
            clean_json = raw_response.strip()
            if clean_json.startswith("```"):
                clean_json = clean_json.split("```")[1]
                if clean_json.startswith("json"):
                    clean_json = clean_json[4:]
            clean_json = clean_json.strip()

            parsed = json.loads(clean_json)

            report = AnalysisReport(
                ticker=ticker,
                analysis_date=analysis_date,
                signal=SentimentSignal(parsed["signal"]),
                confidence_score=float(parsed["confidence_score"]),
                summary=parsed["summary"],
                key_factors=parsed.get("key_factors", []),
                sources_used=parsed.get("sources_used", []),
                raw_llm_response=raw_response,
                model_used=settings.gemini_model,
            )
            logger.success(
                f"[SignalEngine] Signal généré pour {ticker}: "
                f"{report.signal.value} (confiance: {report.confidence_score:.2f})"
            )
            return report

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"[SignalEngine] Erreur parsing JSON pour {ticker}: {e}")
            return AnalysisReport(
                ticker=ticker,
                analysis_date=analysis_date,
                signal=SentimentSignal.NEUTRAL,
                confidence_score=0.0,
                summary=f"Erreur lors de l'analyse: impossible de parser la réponse LLM. {str(e)}",
                key_factors=[],
                sources_used=[],
                raw_llm_response=raw_response,
                model_used=settings.gemini_model,
            )

    def generate_portfolio_summary(
        self,
        reports: list[AnalysisReport],
        analysis_date: Optional[date] = None,
    ) -> str:
        """Génère une synthèse globale du portefeuille."""
        analysis_date = analysis_date or date.today()

        signals_text = "\n".join(
            f"- **{r.ticker}**: {r.signal.value} (confiance: {r.confidence_score:.0%}) — {r.summary[:150]}"
            for r in reports
        )

        chain = PORTFOLIO_SUMMARY_PROMPT | self.llm
        response = chain.invoke(
            {
                "analysis_date": analysis_date.isoformat(),
                "individual_signals": signals_text,
            }
        )
        return response.content
