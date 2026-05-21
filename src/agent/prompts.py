"""Templates de prompts pour l'agent d'analyse financière."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate

# ─── Prompt système principal ─────────────────────────────────────────────────

FINANCIAL_ANALYST_SYSTEM = """Tu es un analyste financier senior spécialisé dans l'analyse de sentiment \
et la génération de signaux d'investissement. Tu analyses des données financières en temps réel \
(cours d'actions, articles de presse, rapports trimestriels) pour produire des synthèses décisionnelles \
précises et actionnables.

Tes analyses doivent être :
- **Objectives** : basées uniquement sur les données fournies, sans biais émotionnel.
- **Structurées** : signal clair (haussier/neutre/baissier) avec justification factuelle.
- **Concises** : synthèse en 3-5 phrases maximum, facteurs clés en liste.
- **Calibrées** : score de confiance honnête (0.0 à 1.0) reflétant la qualité des données disponibles.

Tu réponds TOUJOURS en JSON valide selon le schéma fourni."""

SENTIMENT_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", FINANCIAL_ANALYST_SYSTEM),
        (
            "human",
            """Analyse le sentiment pour le ticker **{ticker}** à la date du {analysis_date}.

## Données disponibles

### Cours récents (30 derniers jours)
{price_data}

### Articles de presse récents
{news_data}

### Contexte RAG (rapports et documents)
{rag_context}

### Indicateurs fondamentaux
{fundamentals}

## Instructions

Génère une analyse de sentiment structurée au format JSON suivant :
```json
{{
  "signal": "haussier" | "neutre" | "baissier",
  "confidence_score": 0.0-1.0,
  "summary": "Synthèse décisionnelle en 3-5 phrases",
  "key_factors": ["facteur 1", "facteur 2", "facteur 3"],
  "sources_used": ["source 1", "source 2"]
}}
```

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire.""",
        ),
    ]
)

# ─── Prompt pour les questions en langage naturel ─────────────────────────────

RAG_QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Tu es un assistant financier expert. Réponds aux questions sur les entreprises \
et les marchés financiers en te basant sur le contexte fourni. \
Si le contexte ne contient pas l'information, dis-le clairement. \
Sois précis, factuel et cite tes sources.""",
        ),
        (
            "human",
            """Contexte extrait des rapports financiers :
{context}

Question : {question}

Réponds en français de manière concise et structurée.""",
        ),
    ]
)

# ─── Prompt de résumé de portefeuille ─────────────────────────────────────────

PORTFOLIO_SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", FINANCIAL_ANALYST_SYSTEM),
        (
            "human",
            """Génère une synthèse globale du portefeuille pour la date du {analysis_date}.

## Signaux individuels
{individual_signals}

## Instructions
Produis une synthèse en 5-7 phrases couvrant :
1. La tendance générale du portefeuille (haussier/neutre/baissier)
2. Les actifs les plus prometteurs et les plus risqués
3. Les thèmes macro-économiques identifiés
4. Une recommandation d'action globale

Réponds en français.""",
        ),
    ]
)
