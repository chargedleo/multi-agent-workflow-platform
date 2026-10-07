"""Retrieval service bridging semantic query embedding and FAISS vector store."""

import time
from typing import List, Optional
from backend.app.core.config import get_settings
from backend.app.core.logging import get_logger
from backend.app.documents.embeddings.provider import get_embedding_provider
from backend.app.documents.schemas import RetrievalResult, RetrievedChunk
from backend.app.documents.vectorstore.faiss_store import get_vector_store

logger = get_logger(__name__)


class RetrievalService:
    """Performs semantic search against indexed document chunks."""

    @staticmethod
    def retrieve(
        query: str,
        top_k: Optional[int] = None,
    ) -> RetrievalResult:
        """Search vector store for chunks matching the query string.

        Args:
            query: Natural language search string.
            top_k: Number of relevant chunks to retrieve (defaults to settings.TOP_K_RETRIEVAL).

        Returns:
            RetrievalResult containing ranked list of RetrievedChunk objects.
        """
        start_time = time.perf_counter()
        settings = get_settings()
        k = top_k if top_k is not None else settings.TOP_K_RETRIEVAL

        clean_query = (query or "").strip()
        if not clean_query:
            return RetrievalResult(query="", results=[])

        vector_store = get_vector_store()
        if vector_store.total_vectors == 0:
            logger.info("Vector index is empty. Returning 0 retrieved chunks.")
            return RetrievalResult(query=clean_query, results=[])

        # 1. Generate query embedding
        embedding_provider = get_embedding_provider()
        query_vector = embedding_provider.embed_query(clean_query)

        # 2. Search FAISS index
        raw_results = vector_store.search(query_vector, top_k=k)

        # 3. Construct strongly typed RetrievedChunk instances
        retrieved_chunks: List[RetrievedChunk] = []
        for chunk_id, score, meta in raw_results:
            retrieved_chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(meta.get("document_id", "")),
                    filename=str(meta.get("filename", "")),
                    content=str(meta.get("content", "")),
                    page_number=int(meta.get("page_number", 1)),
                    similarity_score=round(float(score), 4),
                    metadata=dict(meta),
                )
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            f"Retrieval complete for query '{clean_query[:50]}...': "
            f"{len(retrieved_chunks)} chunks retrieved in {duration_ms}ms (top_k={k})."
        )

        return RetrievalResult(query=clean_query, results=retrieved_chunks)
