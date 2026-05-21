"""Application Streamlit — Interface interactive de veille financière."""

from __future__ import annotations

import os
from datetime import date, timedelta

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─── Configuration ────────────────────────────────────────────────────────────

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

st.set_page_config(
    page_title="Veille Financière LLM",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Helpers API ──────────────────────────────────────────────────────────────


@st.cache_data(ttl=300)
def fetch_prices(ticker: str, limit: int = 90) -> pd.DataFrame:
    """Récupère les cours depuis l'API."""
    try:
        resp = httpx.get(f"{API_BASE_URL}/api/v1/prices/{ticker}", params={"limit": limit})
        resp.raise_for_status()
        return pd.DataFrame(resp.json())
    except Exception as e:
        st.error(f"Erreur API prix: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)
def fetch_latest_analysis(ticker: str) -> dict | None:
    """Récupère la dernière analyse depuis l'API."""
    try:
        resp = httpx.get(f"{API_BASE_URL}/api/v1/analysis/{ticker}/latest")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


@st.cache_data(ttl=300)
def fetch_portfolio_summary(tickers: list[str]) -> dict | None:
    """Récupère le résumé du portefeuille."""
    try:
        resp = httpx.get(
            f"{API_BASE_URL}/api/v1/analysis/portfolio/summary",
            params={"tickers": ",".join(tickers)},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def query_agent(question: str, ticker: str | None = None) -> dict | None:
    """Interroge l'agent LLM."""
    try:
        payload = {"question": question, "ticker": ticker, "include_rag": True}
        resp = httpx.post(
            f"{API_BASE_URL}/api/v1/agent/query",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Erreur agent: {e}")
        return None


# ─── Composants UI ────────────────────────────────────────────────────────────


def signal_badge(signal: str) -> str:
    """Retourne un badge coloré pour le signal."""
    colors = {"haussier": "🟢", "neutre": "🟡", "baissier": "🔴"}
    return colors.get(signal, "⚪")


def render_price_chart(df: pd.DataFrame, ticker: str) -> None:
    """Affiche un graphique de cours avec moyennes mobiles."""
    if df.empty:
        st.warning(f"Aucune donnée de cours pour {ticker}")
        return

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["close"], name="Clôture", line=dict(color="#2196F3")))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma20"], name="MA 20j", line=dict(color="#FF9800", dash="dash")))
    fig.add_trace(go.Scatter(x=df["date"], y=df["ma50"], name="MA 50j", line=dict(color="#9C27B0", dash="dot")))

    fig.update_layout(
        title=f"Cours de {ticker}",
        xaxis_title="Date",
        yaxis_title="Prix (USD)",
        hovermode="x unified",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_volume_chart(df: pd.DataFrame, ticker: str) -> None:
    """Affiche un graphique de volume."""
    if df.empty:
        return
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    fig = px.bar(df, x="date", y="volume", title=f"Volume — {ticker}", color_discrete_sequence=["#4CAF50"])
    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)


# ─── Pages ────────────────────────────────────────────────────────────────────


def page_dashboard() -> None:
    """Page principale — Dashboard du portefeuille."""
    st.title("📊 Dashboard Portefeuille")

    # Sélection des tickers
    selected_tickers = st.multiselect(
        "Tickers suivis",
        options=DEFAULT_TICKERS + ["TSLA", "META"],
        default=DEFAULT_TICKERS,
    )

    if not selected_tickers:
        st.info("Sélectionnez au moins un ticker.")
        return

    # Résumé du portefeuille
    summary = fetch_portfolio_summary(selected_tickers)
    if summary:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tickers suivis", len(selected_tickers))
        col2.metric("🟢 Haussiers", summary.get("bullish_count", 0))
        col3.metric("🟡 Neutres", summary.get("neutral_count", 0))
        col4.metric("🔴 Baissiers", summary.get("bearish_count", 0))

    st.divider()

    # Signaux individuels
    st.subheader("Signaux de sentiment")
    cols = st.columns(min(len(selected_tickers), 3))
    for i, ticker in enumerate(selected_tickers):
        analysis = fetch_latest_analysis(ticker)
        with cols[i % 3]:
            if analysis:
                signal = analysis.get("signal", "neutre")
                confidence = analysis.get("confidence_score", 0)
                st.markdown(
                    f"### {signal_badge(signal)} {ticker}\n"
                    f"**Signal**: {signal.capitalize()}  \n"
                    f"**Confiance**: {confidence:.0%}  \n"
                    f"**Date**: {analysis.get('analysis_date', 'N/A')}"
                )
                with st.expander("Synthèse"):
                    st.write(analysis.get("summary", ""))
                    factors = analysis.get("key_factors", [])
                    if factors:
                        st.markdown("**Facteurs clés:**")
                        for f in factors:
                            st.markdown(f"- {f}")
            else:
                st.markdown(f"### ⚪ {ticker}\n*Aucune analyse disponible*")


def page_ticker_detail() -> None:
    """Page détail d'un ticker."""
    st.title("🔍 Analyse Détaillée")

    ticker = st.selectbox("Sélectionner un ticker", DEFAULT_TICKERS + ["TSLA", "META"])
    period = st.slider("Période (jours)", min_value=30, max_value=365, value=90, step=30)

    df = fetch_prices(ticker, limit=period)
    render_price_chart(df, ticker)
    render_volume_chart(df, ticker)

    # Dernière analyse
    st.subheader("Dernière analyse LLM")
    analysis = fetch_latest_analysis(ticker)
    if analysis:
        signal = analysis.get("signal", "neutre")
        st.markdown(
            f"**{signal_badge(signal)} Signal**: {signal.capitalize()} | "
            f"**Confiance**: {analysis.get('confidence_score', 0):.0%} | "
            f"**Date**: {analysis.get('analysis_date', 'N/A')}"
        )
        st.info(analysis.get("summary", ""))
        factors = analysis.get("key_factors", [])
        if factors:
            st.markdown("**Facteurs clés identifiés:**")
            for f in factors:
                st.markdown(f"- {f}")
    else:
        st.warning("Aucune analyse disponible pour ce ticker.")


def page_agent_chat() -> None:
    """Page chat avec l'agent LLM."""
    st.title("🤖 Agent Financier")
    st.caption("Posez vos questions en langage naturel sur les entreprises et les marchés.")

    # Sélection du ticker (optionnel)
    col1, col2 = st.columns([3, 1])
    with col2:
        ticker_filter = st.selectbox(
            "Filtrer par ticker (optionnel)",
            options=["Tous"] + DEFAULT_TICKERS,
        )
        ticker = None if ticker_filter == "Tous" else ticker_filter

    # Historique de conversation
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input utilisateur
    if prompt := st.chat_input("Ex: Quelle est la situation financière d'Apple ?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyse en cours..."):
                response = query_agent(prompt, ticker)

            if response:
                answer = response.get("answer", "Désolé, je n'ai pas pu générer de réponse.")
                st.markdown(answer)

                sources = response.get("sources", [])
                if sources:
                    with st.expander(f"📚 Sources ({len(sources)})"):
                        for src in sources:
                            st.markdown(f"- {src}")

                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                error_msg = "Erreur lors de la communication avec l'agent."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

    if st.button("🗑️ Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()


# ─── Navigation ───────────────────────────────────────────────────────────────


def main() -> None:
    """Point d'entrée principal de l'application Streamlit."""
    with st.sidebar:
        st.title("📈 Veille Financière LLM")
        st.caption("Powered by GPT-4o + RAG")
        st.divider()

        page = st.radio(
            "Navigation",
            options=["Dashboard", "Analyse Détaillée", "Agent IA"],
            index=0,
        )

        st.divider()
        st.caption(f"API: {API_BASE_URL}")

        # Vérification de l'API
        try:
            resp = httpx.get(f"{API_BASE_URL}/health", timeout=3)
            if resp.status_code == 200:
                st.success("✅ API connectée")
            else:
                st.error("❌ API indisponible")
        except Exception:
            st.error("❌ API non joignable")

    if page == "Dashboard":
        page_dashboard()
    elif page == "Analyse Détaillée":
        page_ticker_detail()
    elif page == "Agent IA":
        page_agent_chat()


if __name__ == "__main__":
    main()
