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
    relevant_chunk_aliases: Optional[List[List[str]]] = None,
) -> RetrievalMetrics:
    """Calculate deterministic IR metrics for a single evaluation case.

    Ground Truth Relevance Convention:
    An item is deemed relevant if its 'chunk_id' matches any 'relevant_chunk_ids'
    (or their explicit equivalence aliases), OR if 'relevant_chunk_ids' is empty
    and its 'document_id' matches any 'relevant_document_ids'.
    Filename-only matching is strictly avoided to prevent false positives across
    unrelated chunks of duplicate documents.

    Equivalence & Duplicate Handling:
    When multiple retrieved chunks belong to the same target concept cluster
    (e.g., duplicated chunks created during repeated test uploads), the first
    occurrence satisfies the concept. Additional duplicates at lower ranks do
    not inflate recall or hit count beyond the concept's single unit of relevance.

    Denominator Conventions:
    - Recall@k: |distinct relevant concepts satisfied in top k| / |total relevant concepts|.
      If total relevant items == 0, Recall is None (undefined), not 0.0 or 1.0.
    - Precision@k: |distinct relevant concepts satisfied in top k| / k.
      Follows standard information retrieval benchmark convention where denominator is k.
    - Hit Rate@k: 1.0 if any relevant item is in top k, else 0.0.
    - MRR: 1 / rank of first relevant item (1-indexed). 0.0 if no relevant item found.
    - MAP: Sum of Precision@r for each newly satisfied relevant hit / total relevant items. 0.0 if no hits.

    Args:
        retrieved_items: Ranked list of retrieved item dictionaries.
        relevant_chunk_ids: List of ground-truth relevant chunk UUIDs.
        relevant_document_ids: Optional list of ground-truth relevant document UUIDs.
        latency_ms: Measured retrieval duration in milliseconds.
        k_values: Ranks to evaluate (defaults to 1, 3, 5).
        relevant_chunk_aliases: Optional list of alias UUID groups for each relevant chunk target.

    Returns:
        Structured RetrievalMetrics model.
    """
    # 1. Build target equivalence clusters
    target_clusters: List[Set[str]] = []
    for idx, cid in enumerate(relevant_chunk_ids):
        cid_clean = str(cid).strip().lower()
        if not cid_clean:
            continue
        cluster = {cid_clean}
        if relevant_chunk_aliases:
            if idx < len(relevant_chunk_aliases) and isinstance(relevant_chunk_aliases[idx], (list, tuple, set)):
                for alias in relevant_chunk_aliases[idx]:
                    alias_clean = str(alias).strip().lower()
                    if alias_clean:
                        cluster.add(alias_clean)
            elif isinstance(relevant_chunk_aliases, (list, tuple)) and all(isinstance(x, str) for x in relevant_chunk_aliases):
                # Flat list of aliases: add all to cluster
                for alias in relevant_chunk_aliases:
                    alias_clean = str(alias).strip().lower()
                    if alias_clean:
                        cluster.add(alias_clean)
        target_clusters.append(cluster)

    clean_doc_targets = {str(did).strip().lower() for did in (relevant_document_ids or []) if str(did).strip()}

    if target_clusters:
        total_relevant = len(target_clusters)
    elif clean_doc_targets:
        total_relevant = len(clean_doc_targets)
    else:
        total_relevant = 0

    # 2. Deduplicate retrieved items while preserving order
    ordered_items = deduplicate_ranked_results(retrieved_items)
    retrieved_count = len(ordered_items)

    def match_target(item: Dict[str, Any]) -> Optional[int]:
        """Return the target cluster index matched by this item, or None."""
        c_id = str(item.get("chunk_id") or "").strip().lower()
        d_id = str(item.get("document_id") or "").strip().lower()

        if target_clusters:
            if c_id:
                for c_idx, cluster in enumerate(target_clusters):
                    if c_id in cluster:
                        return c_idx
            return None
        elif clean_doc_targets:
            if d_id and d_id in clean_doc_targets:
                sorted_docs = sorted(list(clean_doc_targets))
                return sorted_docs.index(d_id)
            return None
        return None

    # 3. Evaluate Hit indicators across ranked positions
    relevance_mask: List[bool] = [match_target(it) is not None for it in ordered_items]

    # 4. Calculate Recall@k, Precision@k, HitRate@k
    metrics_at_k: Dict[str, Any] = {}
    for k in (1, 3, 5):
        top_k_items = ordered_items[:k]
        satisfied_targets: Set[int] = set()
        for it in top_k_items:
            t_idx = match_target(it)
            if t_idx is not None:
                satisfied_targets.add(t_idx)

        distinct_hits = len(satisfied_targets)

        # Recall@k
        if total_relevant == 0:
            rec = None
        else:
            rec = round(min(1.0, distinct_hits / total_relevant), 4)
        metrics_at_k[f"recall_at_{k}"] = rec

        # Precision@k (denominator is k)
        prec = round(distinct_hits / k, 4)
        metrics_at_k[f"precision_at_{k}"] = prec

        # Hit Rate@k
        hr = 1.0 if distinct_hits > 0 else 0.0
        metrics_at_k[f"hit_rate_at_{k}"] = hr

    # 5. MRR: Reciprocal rank of first relevant result
    mrr = 0.0
    for rank_idx, hit in enumerate(relevance_mask, start=1):
        if hit:
            mrr = round(1.0 / rank_idx, 4)
            break

    # 6. MAP: Average Precision across newly satisfied target positions
    if total_relevant == 0 or sum(relevance_mask) == 0:
        map_score = 0.0
    else:
        cum_hits = 0
        prec_sum = 0.0
        seen_targets: Set[int] = set()
        for rank_idx, it in enumerate(ordered_items, start=1):
            t_idx = match_target(it)
            if t_idx is not None and t_idx not in seen_targets:
                seen_targets.add(t_idx)
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
