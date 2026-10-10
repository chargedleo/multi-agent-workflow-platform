"""Deterministic information retrieval (IR) metrics engine (Milestone 9A).

Implements:
- Recall@k (k=1, 3, 5) with documented zero-denominator handling
- Precision@k (k=1, 3, 5) with standard rank denominator
- Hit Rate@k (k=1, 3, 5)
- Mean Reciprocal Rank (MRR)
- Mean Average Precision (MAP)
- Deduplication preserving rank order
- Purely deterministic, offline-evaluable without external network calls
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.evaluation.schemas import RetrievalMetrics


def deduplicate_ranked_results(
    results: List[Dict[str, Any]],
    id_field: str = "chunk_id",
    fallback_id_field: str = "document_id",
) -> List[Dict[str, Any]]:
    """Deduplicate retrieved results by stable identifier while preserving strict ranking order.

    Args:
        results: Ordered list of retrieved chunk/document metadata dictionaries.
        id_field: Primary identifier key (e.g., 'chunk_id').
        fallback_id_field: Secondary identifier key (e.g., 'document_id').

    Returns:
        Deduplicated list preserving first-occurrence order.
    """
    deduped: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for item in results:
        identifier = str(item.get(id_field) or item.get(fallback_id_field) or "")
        if not identifier:
            # If no identifier, include as unique to avoid discarding anonymous chunks
            deduped.append(item)
            continue
        if identifier not in seen:
            seen.add(identifier)
            deduped.append(item)

    return deduped


def compute_retrieval_metrics(
    retrieved_items: List[Dict[str, Any]],
    relevant_chunk_ids: List[str],
    relevant_document_ids: Optional[List[str]] = None,
    latency_ms: float = 0.0,
    k_values: Tuple[int, ...] = (1, 3, 5),
) -> RetrievalMetrics:
    """Calculate deterministic IR metrics for a single evaluation case.

    Ground Truth Relevance Convention:
    An item is deemed relevant if its 'chunk_id' matches any 'relevant_chunk_ids',
    OR if its 'document_id' matches any 'relevant_document_ids'.

    Denominator Conventions:
    - Recall@k: |relevant items in top k| / |total relevant items|.
      If total relevant items == 0, Recall is None (undefined), not 0.0 or 1.0.
    - Precision@k: |relevant items in top k| / k.
      Follows standard information retrieval benchmark convention where denominator is k.
    - Hit Rate@k: 1.0 if any item in top k is relevant, else 0.0.
    - MRR: 1 / rank of first relevant item (1-indexed). 0.0 if no relevant item found.
    - MAP: Sum of Precision@r for each relevant hit / total relevant items. 0.0 if no hits.

    Args:
        retrieved_items: Ranked list of retrieved item dictionaries.
        relevant_chunk_ids: List of ground-truth relevant chunk UUIDs.
        relevant_document_ids: Optional list of ground-truth relevant document UUIDs.
        latency_ms: Measured retrieval duration in milliseconds.
        k_values: Ranks to evaluate (defaults to 1, 3, 5).

    Returns:
        Structured RetrievalMetrics model.
    """
    clean_chunk_targets = {str(cid).strip().lower() for cid in relevant_chunk_ids if str(cid).strip()}
    clean_doc_targets = {str(did).strip().lower() for did in (relevant_document_ids or []) if str(did).strip()}

    total_relevant = len(clean_chunk_targets) or len(clean_doc_targets)

    # 1. Deduplicate retrieved items while preserving order
    ordered_items = deduplicate_ranked_results(retrieved_items)
    retrieved_count = len(ordered_items)

    # Helper function: is item relevant?
    def is_relevant(item: Dict[str, Any]) -> bool:
        c_id = str(item.get("chunk_id") or "").strip().lower()
        d_id = str(item.get("document_id") or "").strip().lower()
        filename = str(item.get("filename") or "").strip().lower()

        if c_id and c_id in clean_chunk_targets:
            return True
        if d_id and d_id in clean_doc_targets:
            return True
        if filename and filename in clean_doc_targets:
            return True
        return False

    # 2. Evaluate Hit indicators across ranked positions
    relevance_mask: List[bool] = [is_relevant(it) for it in ordered_items]

    # 3. Calculate Recall@k, Precision@k, HitRate@k
    metrics_at_k: Dict[str, Any] = {}
    for k in (1, 3, 5):
        top_k_mask = relevance_mask[:k]
        hits = sum(1 for hit in top_k_mask if hit)

        # Recall@k
        if total_relevant == 0:
            rec = None
        else:
            rec = round(min(1.0, hits / total_relevant), 4)
        metrics_at_k[f"recall_at_{k}"] = rec

        # Precision@k (denominator is k)
        prec = round(hits / k, 4)
        metrics_at_k[f"precision_at_{k}"] = prec

        # Hit Rate@k
        hr = 1.0 if hits > 0 else 0.0
        metrics_at_k[f"hit_rate_at_{k}"] = hr

    # 4. MRR: Reciprocal rank of first relevant result
    mrr = 0.0
    for rank_idx, hit in enumerate(relevance_mask, start=1):
        if hit:
            mrr = round(1.0 / rank_idx, 4)
            break

    # 5. MAP: Average Precision across relevant positions
    if total_relevant == 0 or sum(relevance_mask) == 0:
        map_score = 0.0
    else:
        cum_hits = 0
        prec_sum = 0.0
        for rank_idx, hit in enumerate(relevance_mask, start=1):
            if hit:
                cum_hits += 1
                prec_sum += cum_hits / rank_idx
        map_score = round(prec_sum / total_relevant, 4)

    return RetrievalMetrics(
        recall_at_1=metrics_at_k["recall_at_1"],
        recall_at_3=metrics_at_k["recall_at_3"],
        recall_at_5=metrics_at_k["recall_at_5"],
        precision_at_1=metrics_at_k["precision_at_1"],
        precision_at_3=metrics_at_k["precision_at_3"],
        precision_at_5=metrics_at_k["precision_at_5"],
        hit_rate_at_1=metrics_at_k["hit_rate_at_1"],
        hit_rate_at_3=metrics_at_k["hit_rate_at_3"],
        hit_rate_at_5=metrics_at_k["hit_rate_at_5"],
        mrr=mrr,
        map_score=map_score,
        latency_ms=round(latency_ms, 2),
        retrieved_count=retrieved_count,
        relevant_count=total_relevant,
    )
