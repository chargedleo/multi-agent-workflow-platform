"""Deterministic reference-based answer evaluation (Milestone 9A).

Measures:
- Expected-fact coverage via normalized term-matching
- Identification of matched vs missing expected facts
- Correct abstention detection for unanswerable queries
- Structured completeness score
- Documented deterministic grading limitations
"""

import re
from typing import Any, Dict, List, Optional, Set
from backend.app.evaluation.schemas import AnswerMetrics

STOP_WORDS: Set[str] = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "but", "if", "then", "else", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "can", "will",
    "just", "should", "now", "it", "its", "this", "that", "these", "those"
}

ABSTENTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"not (?:mentioned|found|provided|stated|specified|available|in the|documented)", re.I),
    re.compile(r"does not (?:contain|state|mention|provide|indicate|specify)", re.I),
    re.compile(r"cannot (?:be determined|answer|find|locate|confirm)", re.I),
    re.compile(r"no (?:information|mention|record|evidence|data|details) (?:found|available|provided)", re.I),
    re.compile(r"outside (?:the|of) (?:scope|corpus|documentation)", re.I),
    re.compile(r"unable to (?:answer|determine|find)", re.I),
    re.compile(r"unanswerable", re.I),
]


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing and stripping special punctuation."""
    return re.sub(r"[^\w\s]", " ", (text or "").lower())


def extract_key_terms(phrase: str) -> Set[str]:
    """Extract significant content keywords from a factual statement."""
    tokens = normalize_text(phrase).split()
    return {t for t in tokens if len(t) > 2 and t not in STOP_WORDS}


def is_fact_matched(fact: str, answer_text: str) -> bool:
    """Check if an expected fact is present in the answer text via key-term matching."""
    norm_answer = normalize_text(answer_text)
    norm_fact = normalize_text(fact)

    # 1. Direct exact or substring match
    if norm_fact in norm_answer:
        return True

    # 2. Key-term coverage match (at least 75% of content terms found in answer)
    fact_terms = extract_key_terms(fact)
    if not fact_terms:
        return True

    answer_tokens = set(norm_answer.split())
    matched_terms = fact_terms.intersection(answer_tokens)
    coverage = len(matched_terms) / len(fact_terms)
    return coverage >= 0.75


def is_abstaining(answer_text: str) -> bool:
    """Check if answer text indicates refusal or abstention due to lack of evidence."""
    for pattern in ABSTENTION_PATTERNS:
        if pattern.search(answer_text):
            return True
    return False


def compute_answer_metrics(
    answer: str,
    expected_facts: List[str],
    answerable: bool = True,
    key_points: Optional[List[str]] = None,
) -> AnswerMetrics:
    """Evaluate synthesized answer against expected benchmark facts.

    Denominator & Fallback Conventions:
    - If expected_facts is empty and answerable is True: fact_coverage is 1.0.
    - If answerable is False:
        - If answer abstains: correct_abstention is True, fact_coverage is 1.0.
        - If answer does NOT abstain: correct_abstention is False, fact_coverage is 0.0.
    - If answerable is True:
        - correct_abstention is None (not applicable).
        - fact_coverage = |matched_facts| / |expected_facts|.

    Args:
        answer: Synthesized response string from agent.
        expected_facts: List of atomic facts required for the answer.
        answerable: Whether the question was answerable.
        key_points: Optional executive summary bullet points.

    Returns:
        Structured AnswerMetrics model.
    """
    clean_answer = (answer or "").strip()
    kps = key_points or []

    # 1. Unanswerable query handling (Category C)
    if not answerable:
        abstains = is_abstaining(clean_answer)
        return AnswerMetrics(
            fact_coverage=1.0 if abstains else 0.0,
            missing_facts=[] if abstains else ["Expected abstention due to lack of corpus evidence"],
            matched_facts=["Proper abstention"] if abstains else [],
            correct_abstention=abstains,
            completeness_score=1.0 if abstains else 0.0,
            deterministic_grade_note=(
                "Abstention verified via deterministic regex patterns. "
                "Semantic nuance requires M9B model-assisted grading."
            ),
        )

    # 2. Answerable query evaluation
    if not expected_facts:
        return AnswerMetrics(
            fact_coverage=1.0,
            missing_facts=[],
            matched_facts=[],
            correct_abstention=None,
            completeness_score=1.0 if len(clean_answer.split()) > 10 else 0.5,
            deterministic_grade_note="No specific ground truth facts registered; validated structural length.",
        )

    matched: List[str] = []
    missing: List[str] = []

    for fact in expected_facts:
        if is_fact_matched(fact, clean_answer):
            matched.append(fact)
        else:
            missing.append(fact)

    coverage = round(len(matched) / len(expected_facts), 4)

    # Completeness heuristic: reward answer length (>20 words) and key points
    word_count = len(clean_answer.split())
    has_kps = len(kps) > 0
    completeness = 1.0 if (word_count >= 20 and has_kps) else (0.8 if word_count >= 15 else 0.5)

    return AnswerMetrics(
        fact_coverage=coverage,
        missing_facts=missing,
        matched_facts=matched,
        correct_abstention=None,
        completeness_score=completeness,
        deterministic_grade_note=(
            "Evaluated via normalized term and n-gram overlap. "
            "Advanced semantic grading is reserved for M9B."
        ),
    )
