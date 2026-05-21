"""Chaîne RAG pour les questions en langage naturel sur les données financières."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from loguru import logger

from src.agent.chromadb_index import ChromaDBIndex
from src.agent.prompts import RAG_QA_PROMPT
from src.config import settings

if TYPE_CHECKING:
    from src.models.schemas import AgentQueryRequest, AgentQueryResponse


class RAGChain:
    """Chaîne RAG pour les questions financières en langage naturel."""

    def __init__(
        self,
        chroma_index: Optional[ChromaDBIndex] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> None:
        self.chroma_index = chroma_index or ChromaDBIndex()
        self.llm = ChatGoogleGenerativeAI(
            model=model or settings.gemini_model,
            temperature=temperature,
            google_api_key=settings.gemini_api_key,
            convert_system_message_to_human=True,
        )
        self.output_parser = StrOutputParser()

    def _format_context(self, docs: list[Document]) -> str:
        if not docs:
            return "Aucun document pertinent trouvé dans la base de connaissances."
        parts = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            source_info = (
                f"[{meta.get('type', 'document')} | "
                f"{meta.get('ticker', 'N/A')} | "
                f"{meta.get('filing_date', meta.get('published_at', 'N/A'))}]"
            )
            parts.append(f"**Source {i}** {source_info}:\n{doc.page_content}")
        return "\n\n---\n\n".join(parts)

    def query(self, request: "AgentQueryRequest") -> "AgentQueryResponse":
        """Répond à une question en langage naturel via le pipeline RAG."""
        # Import local pour éviter le cycle
        from src.models.schemas import AgentQueryResponse

        logger.info(f"[RAGChain] Question: '{request.question[:80]}'")

        sources: list[str] = []
        context = ""

        if request.include_rag:
            docs = self.chroma_index.similarity_search(
                query=request.question,
                ticker=request.ticker,
                k=6,
                score_threshold=0.25,
            )
            context = self._format_context(docs)
            sources = list(
                {
                    doc.metadata.get("url", doc.metadata.get("file_path", ""))
                    for doc in docs
                    if doc.metadata.get("url") or doc.metadata.get("file_path")
                }
            )
        else:
            context = "Pipeline RAG désactivé pour cette requête."

        chain = RAG_QA_PROMPT | self.llm | self.output_parser
        answer = chain.invoke({"context": context, "question": request.question})

        logger.success(f"[RAGChain] Réponse générée ({len(answer)} caractères)")

        return AgentQueryResponse(
            answer=answer,
            sources=sources,
            ticker=request.ticker,
        )

    def get_retriever(self, ticker: Optional[str] = None, k: int = 5):
        search_kwargs: dict = {"k": k}
        if ticker:
            search_kwargs["filter"] = {"ticker": ticker}
        return self.chroma_index.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs=search_kwargs,
        )
