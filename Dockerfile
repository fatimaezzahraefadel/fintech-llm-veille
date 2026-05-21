FROM python:3.12-slim

WORKDIR /app

# Installer uniquement les dépendances système minimales (pas de gcc)
RUN apt-get update && apt-get install -y \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Installer uv
RUN pip install --no-cache-dir uv==0.2.0

# Copier les fichiers nécessaires au build
COPY pyproject.toml .
COPY README.md .

# Installer les dépendances Python avec uv (binaires pré-compilés, pas de gcc)
RUN uv pip install --system \
    "yfinance>=0.2.40" \
    "newsapi-python>=0.2.7" \
    "requests>=2.32.3" \
    "httpx>=0.27.0" \
    "beautifulsoup4>=4.12.3" \
    "pdfplumber>=0.11.0" \
    "sqlalchemy>=2.0.30" \
    "psycopg2-binary>=2.9.9" \
    "alembic>=1.13.1" \
    "chromadb>=0.5.0" \
    "langchain>=0.2.0" \
    "langchain-text-splitters>=0.2.0" \
    "langchain-google-genai>=1.0.0" \
    "langchain-community>=0.2.0" \
    "langchain-chroma>=0.1.0" \
    "google-generativeai>=0.7.0" \
    "pydantic>=2.7.0" \
    "pydantic-settings>=2.2.0" \
    "fastapi>=0.111.0" \
    "uvicorn[standard]>=0.30.0" \
    "streamlit>=1.35.0" \
    "plotly>=5.22.0" \
    "pandas>=2.2.2" \
    "loguru>=0.7.2" \
    "python-dotenv>=1.0.1" \
    "tenacity>=8.3.0"

# Copier le code source
COPY src/ ./src/
COPY app/ ./app/
COPY dags/ ./dags/

# Créer les répertoires de données
RUN mkdir -p data/chromadb data/pdfs logs

EXPOSE 8000 8501
