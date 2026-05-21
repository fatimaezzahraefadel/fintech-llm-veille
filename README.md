# 📈 Plateforme de Veille Financière Augmentée par LLM

Pipeline ETL multi-sources + agent LLM RAG pour l'analyse de sentiment et la génération de signaux financiers.

## Architecture

```
Sources (Yahoo Finance, NewsAPI, SEC EDGAR, Alpha Vantage)
    ↓
ETL & Stockage (Airflow DAG → PostgreSQL + ChromaDB)
    ↓
Agent IA (LangChain + GPT-4o + RAG)
    ↓
Visualisation (FastAPI + Streamlit + Power BI)
```

## Stack technique

| Couche | Technologies |
|--------|-------------|
| Collecte | `yfinance`, `newsapi-python`, `httpx`, `pdfplumber` |
| Stockage | PostgreSQL, SQLAlchemy, ChromaDB |
| Orchestration | Apache Airflow, Docker Compose |
| Agent IA | LangChain, Gemini 1.5 Pro, embedding-001 |
| API | FastAPI, Pydantic v2 |
| Visualisation | Streamlit, Plotly, Power BI |
| Qualité | pytest, ruff, GitHub Actions |

## Démarrage rapide

### Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — gestionnaire de dépendances
- Docker & Docker Compose
- Clés API : OpenAI, NewsAPI, Alpha Vantage

### Installation

```bash
# 1. Cloner le repo
git clone https://github.com/votre-username/fintech-llm-veille.git
cd fintech-llm-veille

# 2. Copier et remplir les variables d'environnement
cp .env.example .env
# Éditer .env avec vos clés API

# 3. Installer les dépendances avec uv
uv sync

# 4. Lancer la stack complète
docker-compose up -d
```

### Services disponibles

| Service | URL | Description |
|---------|-----|-------------|
| FastAPI | http://localhost:8000/docs | Documentation API Swagger |
| Streamlit | http://localhost:8501 | Application interactive |
| Airflow | http://localhost:8080 | Orchestration (admin/admin) |
| PostgreSQL | localhost:5432 | Base de données |

### Lancement sans Docker (développement)

```bash
# Initialiser la BDD
uv run python -c "from src.models.database import init_db; init_db()"

# Lancer l'API
uv run uvicorn src.api.main:app --reload

# Lancer Streamlit
uv run streamlit run app/streamlit_app.py

# Lancer les tests
uv run pytest tests/ -v
```

## Structure du projet

```
fintech-llm-veille/
├── src/
│   ├── collectors/      # Collecteurs par source de données
│   ├── pipeline/        # ETL, nettoyage, ingestion, déduplication
│   ├── agent/           # RAG chain, prompts, signal engine, ChromaDB
│   ├── api/             # FastAPI + routers
│   └── models/          # Schémas Pydantic + ORM SQLAlchemy
├── dags/                # DAG Airflow quotidien
├── app/                 # Application Streamlit
├── tests/               # Tests unitaires pytest
├── notebooks/           # EDA et explorations
├── dashboards/          # Fichier Power BI
├── docker-compose.yml
└── pyproject.toml
```

## Pipeline Airflow

Le DAG `daily_financial_pipeline` s'exécute chaque jour ouvré à 7h00 :

```
collect_stock_prices ──┐
                       ├──→ index_new_articles → run_llm_analysis → log_summary
collect_news_articles ─┘
```

## Endpoints API principaux

```
GET  /api/v1/prices/{ticker}              Cours historiques
GET  /api/v1/prices/{ticker}/latest       Dernier cours
GET  /api/v1/analysis/{ticker}/latest     Dernière analyse LLM
GET  /api/v1/analysis/portfolio/summary   Résumé du portefeuille
POST /api/v1/agent/query                  Question en langage naturel
GET  /api/v1/agent/index/stats            Stats ChromaDB
```

## Variables d'environnement

| Variable | Description | Requis |
|----------|-------------|--------|
| `GEMINI_API_KEY` | Clé API Google Gemini | ✅ |
| `NEWSAPI_KEY` | Clé API NewsAPI | ✅ |
| `ALPHA_VANTAGE_KEY` | Clé API Alpha Vantage | ✅ |
| `POSTGRES_*` | Connexion PostgreSQL | ✅ |
| `WATCHED_TICKERS` | Tickers suivis (CSV) | ✅ |
| `CHROMA_PERSIST_DIR` | Répertoire ChromaDB | ✅ |

## Ligne CV

> **Plateforme de veille financière IA** — Pipeline ETL multi-sources (Yahoo Finance, NewsAPI, SEC EDGAR), stockage PostgreSQL, agent LLM RAG (LangChain + GPT-4o + ChromaDB) pour analyse de sentiment et génération de signaux financiers, orchestration Airflow, dashboards Power BI & app Streamlit déployée.

## Licence

MIT
