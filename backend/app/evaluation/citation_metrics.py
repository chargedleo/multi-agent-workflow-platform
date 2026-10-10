"""Deterministic citation integrity metrics (Milestone 9A).

Measures:
- Citation presence (when required vs abstention)
- Identifier validity (non-empty UUID / filename)
- Source reference validity (grounded in actual retrieved documents)
- Page reference validity (verified against retrieved page metadata)
- Attribution match (matching ground-truth benchmark citations)
- Duplicate and malformed citation detection
"""

from typing import Any, Dict, List, Optional, Set
from backend.app.evaluation.schemas import CitationMetrics, ExpectedCitation


def compute_citation_metrics(
    citations: List[Dict[str, Any]],
    retrieved_documents: List[Dict[str, Any]],
    expected_citations: Optional[List[ExpectedCitation]] = None,
    answerable: bool = True,
) -> CitationMetrics:
    """Calculate deterministic citation integrity metrics.

    Denominator & Fallback Conventions:
    - If answerable is False and citations == 0: presence is 1.0 (correctly cited no evidence).
    - If answerable is False and citations > 0: presence is 0.0 (hallucinated citations for unanswerable query).
    - If no citations and none expected: all rates are 1.0.
    - If no citations and citations expected: presence is 0.0, rates are 0.0.

    Args:
        citations: List of source citation dicts from the agent response.
        retrieved_documents: List of chunk/doc dicts actually returned by retriever.
        expected_citations: Ground-truth expected citations from benchmark case.
        answerable: Whether the question was answerable.

    Returns:
        Structured CitationMetrics model.
    """
    total_citations = len(citations)
    expected = expected_citations or []
    has_expected = len(expected) > 0

    # 1. Unanswerable case handling
    if not answerable:
        if total_citations == 0:
            return CitationMetrics(
                citation_presence=1.0,
                identifier_validity=1.0,
                source_reference_validity=1.0,
                page_reference_validity=1.0,
                attribution_match=1.0,
                duplicate_citations_count=0,
                malformed_citations_count=0,
                total_citations=0,
            )
        else:
            # Hallucinated citations when query should have abstained
            return CitationMetrics(
                citation_presence=0.0,
                identifier_validity=1.0,
                source_reference_validity=0.0,
                page_reference_validity=0.0,
                attribution_match=0.0,
                duplicate_citations_count=0,
                malformed_citations_count=0,
                total_citations=total_citations,
            )

    # 2. Answerable case with zero citations
    if total_citations == 0:
        presence = 0.0 if has_expected else 1.0
        return CitationMetrics(
            citation_presence=presence,
            identifier_validity=0.0 if has_expected else 1.0,
            source_reference_validity=0.0 if has_expected else 1.0,
            page_reference_validity=0.0 if has_expected else 1.0,
            attribution_match=0.0 if has_expected else 1.0,
            duplicate_citations_count=0,
            malformed_citations_count=0,
            total_citations=0,
        )

    # 3. Build index of verified retrieved documents & chunks
    valid_doc_ids: Set[str] = set()
    valid_filenames: Set[str] = set()
    valid_chunk_ids: Set[str] = set()
    doc_to_pages: Dict[str, Set[int]] = {}

    for doc in retrieved_documents:
        d_id = str(doc.get("document_id") or "").strip().lower()
        fn = str(doc.get("filename") or "").strip().lower()
        c_id = str(doc.get("chunk_id") or "").strip().lower()
        p_num = doc.get("page_number")

        if d_id:
            valid_doc_ids.add(d_id)
            if d_id not in doc_to_pages:
                doc_to_pages[d_id] = set()
            if p_num is not None:
                try:
                    doc_to_pages[d_id].add(int(p_num))
                except (ValueError, TypeError):
                    pass

        if fn:
            valid_filenames.add(fn)
            if fn not in doc_to_pages:
                doc_to_pages[fn] = set()
            if p_num is not None:
                try:
                    doc_to_pages[fn].add(int(p_num))
                except (ValueError, TypeError):
                    pass

        if c_id:
            valid_chunk_ids.add(c_id)

    # 4. Evaluate each citation
    valid_id_count = 0
    source_valid_count = 0
    page_valid_count = 0
    page_testable_count = 0
    malformed_count = 0
    seen_references: Set[str] = set()
    duplicate_count = 0

    for cit in citations:
        if not isinstance(cit, dict):
            malformed_count += 1
            continue

        d_id = str(cit.get("document_id") or "").strip().lower()
        fn = str(cit.get("filename") or "").strip().lower()
        c_id = str(cit.get("chunk_id") or "").strip().lower()
        page = cit.get("page_number")
        snippet = str(cit.get("snippet") or "").strip()

        # Identifier validity: must have non-empty document_id or filename
        if d_id or fn or c_id:
            valid_id_count += 1
        else:
            malformed_count += 1

        # Duplicate check
        dup_key = f"{d_id}:{fn}:{c_id}:{page}:{snippet[:30]}"
        if dup_key in seen_references:
            duplicate_count += 1
        else:
            seen_references.add(dup_key)

        # Source reference validity: cited source must exist in retrieved pool
        is_grounded = False
        if d_id and d_id in valid_doc_ids:
            is_grounded = True
        elif fn and fn in valid_filenames:
            is_grounded = True
        elif c_id and c_id in valid_chunk_ids:
            is_grounded = True

        if is_grounded:
            source_valid_count += 1

        # Page reference validity
        if page is not None:
            try:
                page_int = int(page)
                page_testable_count += 1
                lookup_key = d_id if d_id in doc_to_pages else (fn if fn in doc_to_pages else None)
                if lookup_key and doc_to_pages[lookup_key]:
                    if page_int in doc_to_pages[lookup_key]:
                        page_valid_count += 1
                else:
                    # No page metadata stored on doc, treat as valid/neutral
                    page_valid_count += 1
            except (ValueError, TypeError):
                malformed_count += 1

    identifier_rate = round(valid_id_count / total_citations, 4)
    source_valid_rate = round(source_valid_count / total_citations, 4)
    page_valid_rate = (
        round(page_valid_count / page_testable_count, 4) if page_testable_count > 0 else 1.0
    )

    # 5. Attribution matching against expected citations
    if not has_expected:
        attribution_match = 1.0
    else:
        matched_expected = 0
        for exp in expected:
            exp_fn = str(exp.filename or "").strip().lower()
            exp_doc = str(exp.document_id or "").strip().lower()
            exp_chunk = str(exp.chunk_id or "").strip().lower()

            hit = False
            for cit in citations:
                if not isinstance(cit, dict):
                    continue
                c_fn = str(cit.get("filename") or "").strip().lower()
                c_doc = str(cit.get("document_id") or "").strip().lower()
                c_chunk = str(cit.get("chunk_id") or "").strip().lower()

                if exp_fn and exp_fn in c_fn:
                    hit = True
                    break
                if exp_doc and exp_doc == c_doc:
                    hit = True
                    break
                if exp_chunk and exp_chunk == c_chunk:
                    hit = True
                    break
            if hit:
                matched_expected += 1

        attribution_match = round(matched_expected / len(expected), 4)

    return CitationMetrics(
        citation_presence=1.0,
        identifier_validity=identifier_rate,
        source_reference_validity=source_valid_rate,
        page_reference_validity=page_valid_rate,
        attribution_match=attribution_match,
        duplicate_citations_count=duplicate_count,
        malformed_citations_count=malformed_count,
        total_citations=total_citations,
    )
