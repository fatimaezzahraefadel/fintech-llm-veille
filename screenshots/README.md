# 📸 Guide des Captures d'Écran — Plateforme de Veille Financière LLM

Ce dossier contient les captures essentielles pour documenter le projet.
Suis ce guide dans l'ordre pour obtenir les meilleures captures.

---

## ✅ Checklist avant de commencer

- [ ] Containers Docker en cours d'exécution (`docker-compose -f docker-compose.dev.yml up -d`)
- [ ] Données collectées (script `collect_initial_data.py` exécuté)
- [ ] API accessible sur http://localhost:8000
- [ ] Streamlit accessible sur http://localhost:8501

---

## 📋 Liste des captures (dans l'ordre)

---

### 01 — Architecture Docker — Containers en cours d'exécution
**Fichier :** `01_docker_containers_running.png`

**Où :** Docker Desktop → onglet "Containers"

**Comment :**
1. Ouvre Docker Desktop
2. Clique sur "Containers" dans le menu gauche
3. Tu dois voir 3 containers verts : `postgres`, `api`, `streamlit`
4. Capture l'écran complet montrant les 3 containers avec leur statut "Running"

**Ce que ça montre :** La stack complète est opérationnelle (PostgreSQL + FastAPI + Streamlit)

---

### 02 — API FastAPI — Documentation Swagger
**Fichier :** `02_fastapi_swagger_docs.png`

**Où :** http://localhost:8000/docs

**Comment :**
1. Ouvre http://localhost:8000/docs dans ton navigateur
2. Laisse la page se charger complètement
3. Capture la page entière montrant tous les endpoints groupés par catégorie
4. (Optionnel) Déplie un endpoint pour montrer les paramètres

**Ce que ça montre :** L'API REST documentée avec tous les endpoints (prix, analyses, agent)

---

### 03 — API FastAPI — Health Check en direct
**Fichier :** `03_api_health_check.png`

**Où :** http://localhost:8000/health

**Comment :**
1. Ouvre http://localhost:8000/health dans ton navigateur
2. Tu dois voir le JSON : `{"status": "ok", "model": "gemini-1.5-pro", "tickers": [...]}`
3. Capture la réponse JSON dans le navigateur

**Ce que ça montre :** L'API tourne avec Gemini 1.5 Pro et les 5 tickers configurés

---

### 04 — API FastAPI — Cours AAPL en temps réel
**Fichier :** `04_api_prices_aapl.png`

**Où :** http://localhost:8000/docs → `GET /api/v1/prices/{ticker}`

**Comment :**
1. Va sur http://localhost:8000/docs
2. Clique sur `GET /api/v1/prices/{ticker}` → "Try it out"
3. Entre `AAPL` dans le champ ticker, `limit` = 10
4. Clique "Execute"
5. Capture la réponse JSON avec les cours réels

**Ce que ça montre :** Les données Yahoo Finance stockées en PostgreSQL et exposées via l'API

---

### 05 — Streamlit — Dashboard Principal
**Fichier :** `05_streamlit_dashboard.png`

**Où :** http://localhost:8501

**Comment :**
1. Ouvre http://localhost:8501
2. La page "Dashboard" s'affiche par défaut
3. Attends que les données se chargent
4. Capture la page complète avec les métriques du portefeuille en haut
5. Si les signaux LLM ne sont pas encore générés, les cartes afficheront "Aucune analyse disponible" — c'est normal

**Ce que ça montre :** L'interface principale de veille avec les signaux par ticker

---

### 06 — Streamlit — Graphique de Cours Interactif
**Fichier :** `06_streamlit_price_chart.png`

**Où :** http://localhost:8501 → "Analyse Détaillée"

**Comment :**
1. Dans Streamlit, clique sur "Analyse Détaillée" dans le menu gauche
2. Sélectionne `NVDA` dans le dropdown
3. Mets la période à 90 jours
4. Capture le graphique avec les courbes de prix + moyennes mobiles MA20/MA50
5. Inclus aussi le graphique de volume en dessous

**Ce que ça montre :** Visualisation interactive des cours avec indicateurs techniques

---

### 07 — Streamlit — Agent IA (Chat)
**Fichier :** `07_streamlit_agent_chat.png`

**Où :** http://localhost:8501 → "Agent IA"

**Comment :**
1. Clique sur "Agent IA" dans le menu gauche
2. Dans le chat, tape cette question :
   `"Quelle est la tendance récente de NVIDIA et quels sont les risques principaux ?"`
3. Attends la réponse de Gemini (10-20 secondes)
4. Capture la conversation complète avec la question et la réponse

**Ce que ça montre :** L'agent LLM répond en langage naturel avec le pipeline RAG

---

### 08 — PostgreSQL — Données en Base
**Fichier :** `08_postgresql_data.png`

**Où :** http://localhost:8000/docs → `GET /api/v1/prices/MSFT`

**Comment :**
1. Va sur http://localhost:8000/docs
2. Teste `GET /api/v1/prices/MSFT` avec limit=5
3. Capture la réponse montrant les données structurées (date, open, close, volume)

**Alternative :** Si tu as DBeaver ou pgAdmin installé :
1. Connecte-toi à `localhost:5434` (user: fintech, password: fintech_secret, db: fintech_veille)
2. Fais un `SELECT * FROM stock_prices LIMIT 20`
3. Capture le tableau de résultats

**Ce que ça montre :** Les données financières structurées stockées en PostgreSQL

---

### 09 — Analyse LLM — Signal de Sentiment Généré
**Fichier :** `09_llm_sentiment_signal.png`

**Où :** http://localhost:8000/docs → `POST /api/v1/agent/query`

**Comment :**
1. Va sur http://localhost:8000/docs
2. Clique sur `POST /api/v1/agent/query` → "Try it out"
3. Entre ce body JSON :
```json
{
  "question": "Analyse le sentiment pour Apple (AAPL) basé sur les dernières nouvelles",
  "ticker": "AAPL",
  "include_rag": false
}
```
4. Clique "Execute"
5. Capture la réponse avec l'analyse générée par Gemini

**Ce que ça montre :** Le LLM génère une analyse de sentiment en temps réel

---

### 10 — Pipeline Complet — Vue d'ensemble
**Fichier :** `10_pipeline_overview.png`

**Où :** Ton terminal / PowerShell

**Comment :**
1. Ouvre un terminal dans le dossier `fintech-llm-veille`
2. Lance : `docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"`
3. Capture le terminal montrant les 3 containers actifs avec leurs ports

**Ce que ça montre :** La stack Docker complète en production locale

---

## 🎯 Captures Bonus (optionnelles)

### 11 — Airflow DAG (si lancé)
**Fichier :** `11_airflow_dag.png`
- URL : http://localhost:8080 (admin/admin)
- Montre le DAG `daily_financial_pipeline` avec ses 5 tâches

### 12 — Streamlit — Sélection Multi-Tickers
**Fichier :** `12_streamlit_portfolio.png`
- Dashboard avec les 5 tickers sélectionnés simultanément

---

## 📁 Nommage des fichiers

```
screenshots/
├── 01_docker_containers_running.png
├── 02_fastapi_swagger_docs.png
├── 03_api_health_check.png
├── 04_api_prices_aapl.png
├── 05_streamlit_dashboard.png
├── 06_streamlit_price_chart.png
├── 07_streamlit_agent_chat.png
├── 08_postgresql_data.png
├── 09_llm_sentiment_signal.png
├── 10_pipeline_overview.png
└── README.md  ← ce fichier
```

---

## 💡 Conseils pour de belles captures

- **Résolution** : Utilise une fenêtre de navigateur à 1280×800 minimum
- **Zoom navigateur** : 90% pour voir plus de contenu
- **Outil Windows** : `Win + Shift + S` pour capturer une zone précise
- **Outil recommandé** : [ShareX](https://getsharex.com/) (gratuit) pour des captures annotées
- **Format** : PNG de préférence (meilleure qualité que JPG pour du texte)
- **Annotations** : Ajoute des flèches rouges pour pointer les éléments importants

---

*Ces captures serviront pour le README GitHub, le portfolio LinkedIn et les présentations.*
