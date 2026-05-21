"""Configuration centralisée via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application chargés depuis les variables d'environnement."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Google Gemini ────────────────────────────────────────────────────────
    gemini_api_key: str = Field(..., description="Clé API Google Gemini")
    gemini_model: str = Field(
        default="gemini-2.0-flash", description="Modèle Gemini à utiliser"
    )
    gemini_embedding_model: str = Field(
        default="models/text-embedding-004", description="Modèle d'embedding Gemini"
    )

    # ─── NewsAPI ──────────────────────────────────────────────────────────────
    newsapi_key: str = Field(..., description="Clé API NewsAPI")

    # ─── Alpha Vantage ────────────────────────────────────────────────────────
    alpha_vantage_key: str = Field(..., description="Clé API Alpha Vantage")

    # ─── PostgreSQL ───────────────────────────────────────────────────────────
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="fintech_veille")
    postgres_user: str = Field(default="fintech")
    postgres_password: str = Field(default="fintech_secret")

    # ─── ChromaDB ─────────────────────────────────────────────────────────────
    chroma_persist_dir: str = Field(default="./data/chromadb")
    chroma_collection_name: str = Field(default="financial_reports")

    # ─── Application ──────────────────────────────────────────────────────────
    log_level: str = Field(default="INFO")
    environment: str = Field(default="development")
    watched_tickers: str = Field(default="AAPL,MSFT,GOOGL,AMZN,NVDA")

    # ─── Computed ─────────────────────────────────────────────────────────────
    @computed_field  # type: ignore[misc]
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def tickers_list(self) -> list[str]:
        return [t.strip().upper() for t in self.watched_tickers.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance singleton des settings (mise en cache)."""
    return Settings()  # type: ignore[call-arg]


# Instance globale
settings = get_settings()
