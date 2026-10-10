"""Retrieval service adapter for the Evaluation Engine (Milestone 9A).

Adapts real production RetrievalService.retrieve results into standard evaluation
dictionaries without reimplementing or altering production FAISS retrieval behavior.
"""

import time
from typing import Any, Dict, List, Tuple

from backend.app.core.logging import get_logger
from backend.app.documents.schemas import RetrievalResult
from backend.app.services.retrieval import RetrievalService

logger = get_logger(__name__)


def execute_evaluation_retrieval(
    query: str,
    top_k: int = 5,
) -> Tuple[List[Dict[str, Any]], float]:
    """Invoke real production RetrievalService and normalize results into evaluation representation.

    Args:
        query: User search query.
        top_k: Number of chunks to retrieve.

    Returns:
        Tuple of (normalized_retrieved_items, measured_latency_ms).
    """
    start_time = time.perf_counter()
    try:
        raw_result: RetrievalResult = RetrievalService.retrieve(query=query, top_k=top_k)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        normalized: List[Dict[str, Any]] = []
        for chunk in raw_result.results:
            normalized.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "similarity_score": chunk.similarity_score,
                    "metadata": chunk.metadata,
                }
            )

        return normalized, round(duration_ms, 2)
    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.warning(f"Evaluation retrieval execution encountered error for query '{query[:40]}...': {exc}")
        return [], round(duration_ms, 2)
