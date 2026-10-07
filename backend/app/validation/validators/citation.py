"""Citation and source provenance validator.

Ensures that all citations attached to the final response correspond to actual,
verified documents and chunks retrieved during the workflow run. Prevents hallucinated
or fabricated document references.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
from backend.app.validation.schemas import (
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)


def validate_citations(
    final_answer: Optional[Dict[str, Any]],
    state: Dict[str, Any],
) -> Tuple[List[ValidationIssue], int]:
    """Validate citations against retrieved documents.

    Returns:
        Tuple of (recorded_issues, checked_count)
    """
    issues: List[ValidationIssue] = []
    checks = 0

    if not final_answer:
        return issues, checks

    sources = final_answer.get("sources") or []
    retrieved_docs = state.get("retrieved_documents") or []

    # Map available retrieved documents and chunks
    valid_doc_ids: Set[str] = set()
    valid_chunk_ids: Set[str] = set()
    doc_id_to_pages: Dict[str, Set[int]] = {}

    for doc in retrieved_docs:
        d_id = str(doc.get("document_id") or "")
        c_id = str(doc.get("chunk_id") or "")
        meta = doc.get("metadata") or {}
        p_num = meta.get("page_number") or doc.get("page_number")

        if d_id:
            valid_doc_ids.add(d_id)
            if d_id not in doc_id_to_pages:
                doc_id_to_pages[d_id] = set()
            if p_num is not None:
                try:
                    doc_id_to_pages[d_id].add(int(p_num))
                except (ValueError, TypeError):
                    pass

        if c_id:
            valid_chunk_ids.add(c_id)

    # 1. Missing citations check when documents were retrieved and referenced
    checks += 1
    user_query = (state.get("user_query") or "").lower()
    answer_text = (final_answer.get("answer") or "").lower()
    doc_keywords = ["document", "architecture", "specification", "section", "guide", "pdf", "file"]
    query_mentions_docs = any(kw in user_query for kw in doc_keywords)
    answer_mentions_docs = any(kw in answer_text for kw in ["according to", "section 1", "section 2", "document states", "architecture specification"])

    if retrieved_docs and not sources and (query_mentions_docs or answer_mentions_docs):
        issues.append(
            ValidationIssue(
                code="MISSING_DOCUMENT_CITATIONS",
                severity=ValidationSeverity.ERROR,
                category=ValidationCategory.CITATION_PROVENANCE,
                message="Retrieved documents are available and referenced, but final response contains no citations.",
                evidence=f"retrieved_count={len(retrieved_docs)}, sources_count=0",
                recoverable=True,
                source="citation",
            )
        )

    # 2. Validate each citation
    seen_chunk_ids: Set[str] = set()
    seen_doc_snippets: Set[Tuple[str, str]] = set()

    for idx, src in enumerate(sources):
        checks += 1
        if not isinstance(src, dict):
            issues.append(
                ValidationIssue(
                    code="MALFORMED_CITATION_OBJECT",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.CITATION_PROVENANCE,
                    message=f"Citation at index {idx} is not a valid dictionary object.",
                    recoverable=True,
                    source="citation",
                )
            )
            continue

        doc_id = str(src.get("document_id") or "")
        chunk_id = str(src.get("chunk_id") or "")
        page_num = src.get("page_number")
        snippet = src.get("snippet") or ""

        # Check for fabricated / non-existent document ID
        checks += 1
        if not doc_id:
            issues.append(
                ValidationIssue(
                    code="EMPTY_DOCUMENT_ID",
                    severity=ValidationSeverity.ERROR,
                    category=ValidationCategory.CITATION_PROVENANCE,
                    message=f"Citation at index {idx} is missing a document_id.",
                    recoverable=True,
                    source="citation",
                )
            )
        elif valid_doc_ids and doc_id not in valid_doc_ids:
            issues.append(
                ValidationIssue(
                    code="FABRICATED_DOCUMENT_CITATION",
                    severity=ValidationSeverity.CRITICAL,
                    category=ValidationCategory.CITATION_PROVENANCE,
                    message=f"Citation references unverified document_id '{doc_id}' not present in retrieval results.",
                    evidence=f"cited_doc_id='{doc_id}', valid_doc_ids={list(valid_doc_ids)[:3]}",
                    recoverable=False,
                    source="citation",
                )
            )

        # Check chunk ID if supplied
        if chunk_id:
            checks += 1
            if valid_chunk_ids and chunk_id not in valid_chunk_ids:
                issues.append(
                    ValidationIssue(
                        code="FABRICATED_CHUNK_CITATION",
                        severity=ValidationSeverity.ERROR,
                        category=ValidationCategory.CITATION_PROVENANCE,
                        message=f"Citation references chunk_id '{chunk_id}' not found in retrieved chunks.",
                        evidence=f"cited_chunk_id='{chunk_id}'",
                        recoverable=True,
                        source="citation",
                    )
                )

        # Check duplicate citation
        checks += 1
        dup_key = (doc_id, snippet[:50])
        if chunk_id and chunk_id in seen_chunk_ids:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_CITATION",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.CITATION_PROVENANCE,
                    message=f"Citation chunk '{chunk_id}' is cited multiple times.",
                    evidence=f"chunk_id={chunk_id}",
                    recoverable=True,
                    source="citation",
                )
            )
        elif dup_key in seen_doc_snippets:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_CITATION_SNIPPET",
                    severity=ValidationSeverity.WARNING,
                    category=ValidationCategory.CITATION_PROVENANCE,
                    message=f"Duplicate snippet cited for document '{doc_id}'.",
                    recoverable=True,
                    source="citation",
                )
            )
        else:
            if chunk_id:
                seen_chunk_ids.add(chunk_id)
            seen_doc_snippets.add(dup_key)

        # Validate page number plausibility if supplied
        if page_num is not None:
            checks += 1
            try:
                p_int = int(page_num)
                if p_int < 1:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_PAGE_NUMBER",
                            severity=ValidationSeverity.WARNING,
                            category=ValidationCategory.CITATION_PROVENANCE,
                            message=f"Citation specifies invalid page number {p_int}.",
                            evidence=f"page_number={page_num}",
                            recoverable=True,
                            source="citation",
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        code="MALFORMED_PAGE_NUMBER",
                        severity=ValidationSeverity.WARNING,
                        category=ValidationCategory.CITATION_PROVENANCE,
                        message=f"Citation specifies non-numeric page number '{page_num}'.",
                        recoverable=True,
                        source="citation",
                    )
                )

    return issues, checks
