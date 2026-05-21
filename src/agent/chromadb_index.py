"""Gestion de l'index vectoriel ChromaDB pour le pipeline RAG."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from src.config import settings


class ChromaDBIndex:
    """Gère l'indexation et la recherche sémantique dans ChromaDB."""

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name

        # Créer le répertoire de persistance
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # Embeddings Gemini
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.gemini_embedding_model,
            google_api_key=settings.gemini_api_key,
        )

        self.vectorstore = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_dir,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        logger.info(
            f"[ChromaDB] Index initialisé: {self.collection_name} @ {self.persist_dir}"
        )

    def index_document(
        self,
        text: str,
        metadata: dict,
        doc_id: Optional[str] = None,
    ) -> int:
        """
        Indexe un document texte dans ChromaDB.

        Args:
            text: Contenu textuel du document.
            metadata: Métadonnées (ticker, date, source, type).
            doc_id: Identifiant unique optionnel.

        Returns:
            Nombre de chunks indexés.
        """
        if not text.strip():
            logger.warning("[ChromaDB] Document vide ignoré")
            return 0

        chunks = self.text_splitter.split_text(text)
        documents = [
            Document(
                page_content=chunk,
                metadata={**metadata, "chunk_index": i, "total_chunks": len(chunks)},
            )
            for i, chunk in enumerate(chunks)
        ]

        ids = None
        if doc_id:
            ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

        self.vectorstore.add_documents(documents, ids=ids)
        logger.info(
            f"[ChromaDB] {len(chunks)} chunks indexés pour {metadata.get('ticker', 'N/A')}"
        )
        return len(chunks)

    def index_news_articles(self, articles: list[dict]) -> int:
        """
        Indexe une liste d'articles de presse.

        Args:
            articles: Liste de dicts avec keys: ticker, title, content, published_at, url.

        Returns:
            Nombre total de chunks indexés.
        """
        total = 0
        for article in articles:
            text = f"{article.get('title', '')}\n\n{article.get('content', '')}"
            metadata = {
                "ticker": article.get("ticker", ""),
                "source": "newsapi",
                "type": "news_article",
                "published_at": str(article.get("published_at", "")),
                "url": article.get("url", ""),
            }
            doc_id = article.get("content_hash")
            total += self.index_document(text, metadata, doc_id)
        return total

    def index_sec_report(
        self,
        text: str,
        ticker: str,
        form_type: str,
        filing_date: str,
        file_path: str = "",
    ) -> int:
        """Indexe un rapport SEC (10-K ou 10-Q)."""
        metadata = {
            "ticker": ticker,
            "source": "sec_edgar",
            "type": f"sec_{form_type.lower().replace('-', '')}",
            "filing_date": filing_date,
            "file_path": file_path,
        }
        doc_id = f"{ticker}_{form_type}_{filing_date}"
        return self.index_document(text, metadata, doc_id)

    def similarity_search(
        self,
        query: str,
        ticker: Optional[str] = None,
        k: int = 5,
        score_threshold: float = 0.3,
    ) -> list[Document]:
        """
        Recherche sémantique dans l'index.

        Args:
            query: Question ou requête en langage naturel.
            ticker: Filtrer par ticker (optionnel).
            k: Nombre de résultats à retourner.
            score_threshold: Score de similarité minimum.

        Returns:
            Liste de Documents pertinents.
        """
        filter_dict = {"ticker": ticker} if ticker else None

        try:
            results = self.vectorstore.similarity_search_with_relevance_scores(
                query,
                k=k,
                filter=filter_dict,
            )
            filtered = [doc for doc, score in results if score >= score_threshold]
            logger.debug(
                f"[ChromaDB] {len(filtered)}/{len(results)} résultats au-dessus du seuil "
                f"({score_threshold}) pour: '{query[:50]}...'"
            )
            return filtered
        except Exception as e:
            logger.error(f"[ChromaDB] Erreur de recherche: {e}")
            return []

    def get_collection_stats(self) -> dict:
        """Retourne les statistiques de la collection."""
        count = self.vectorstore._collection.count()
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_dir": self.persist_dir,
        }

    def delete_by_ticker(self, ticker: str) -> None:
        """Supprime tous les documents d'un ticker de l'index."""
        self.vectorstore._collection.delete(where={"ticker": ticker})
        logger.info(f"[ChromaDB] Documents supprimés pour {ticker}")
