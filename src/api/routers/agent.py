"""Endpoints pour l'agent LLM (questions en langage naturel)."""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException

from src.agent.chromadb_index import ChromaDBIndex
from src.agent.rag_chain import RAGChain
from src.models.schemas import AgentQueryRequest, AgentQueryResponse

router = APIRouter(prefix="/agent", tags=["Agent LLM"])


@lru_cache(maxsize=1)
def _get_rag_chain() -> RAGChain:
    """Singleton de la chaîne RAG (initialisée une seule fois)."""
    return RAGChain(chroma_index=ChromaDBIndex())


@router.post(
    "/query",
    response_model=AgentQueryResponse,
    summary="Interroger l'agent en langage naturel",
)
async def query_agent(request: AgentQueryRequest) -> AgentQueryResponse:
    """
    Pose une question en langage naturel à l'agent financier.

    L'agent utilise le pipeline RAG pour récupérer le contexte pertinent
    depuis les rapports indexés et génère une réponse via Gemini 1.5 Pro.
    """
    try:
        chain = _get_rag_chain()
        return chain.query(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur agent: {str(e)}")


@router.get(
    "/index/stats",
    summary="Statistiques de l'index vectoriel",
)
def get_index_stats() -> dict:
    """Retourne les statistiques de la base vectorielle ChromaDB."""
    try:
        index = ChromaDBIndex()
        return index.get_collection_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur ChromaDB: {str(e)}")
