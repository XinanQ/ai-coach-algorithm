"""Shared coverage / gap module.

Both retrieval sides reduce to the same idea: "which expected dimensions did the
employee answer actually cover, and which are missing?". The gap (missing
dimensions) drives tutor scoring (penalize omissions) and customer follow-up
(ask about what was not addressed). Only the granularity differs:

- tutor side:    expected = criterion.must_points  (clause-level, semantic + keyword)
- customer side: expected = profile.expected_intents (intent-level, set difference)
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

from app.core.embedding_adapter import EmbeddingAdapter
from app.core.text_cleaner import clean_text


# Negative pattern keywords - when these appear near must-point keywords,
# the mention should NOT count as coverage (employee is negating the point)
# Reduced list to avoid false positives (e.g., "不错" should not be negated)
NEGATIVE_PATTERNS = [
    # Strong negations (must appear directly before keyword to count)
    "不是", "没有", "不含", "缺乏", "缺失",
    # Unable/cannot (context-dependent)
    "无法", "做不到",
]

# Negative patterns that require stricter positioning (must be immediately before)
STRICT_NEGATIVE_PATTERNS = [
    "不", "没", "无", "别",
]

# Partial coverage indicators - these suggest the employee started on a point
# but didn't fully address it
PARTIAL_PATTERNS = [
    "一定程度上", "部分", "一些", "有点", "稍微", "大致",
    "可能", "应该", "大概", "基本", "差不多",
]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _check_negative_context(answer: str, keyword: str, window: int = 15) -> bool:
    """Check if a keyword appears in a negative context.

    Looks for negative pattern words within `window` characters before the keyword.
    Uses stricter logic to avoid false positives.

    Rules:
    - Strong negations (不是, 没有) can appear within window before keyword
    - Single-character negations (不, 没) must be immediately adjacent (within 3 chars)
    """
    answer_lower = answer.lower()
    keyword_lower = keyword.lower()

    # Find all occurrences of the keyword
    start = 0
    while True:
        idx = answer_lower.find(keyword_lower, start)
        if idx == -1:
            break

        # Check window BEFORE the keyword (negation typically precedes)
        window_start = max(0, idx - window)
        window_end = idx  # Only check before, not after
        context = answer_lower[window_start:window_end]

        # Check for strong negative patterns (can be within window)
        for neg_word in NEGATIVE_PATTERNS:
            if neg_word in context:
                # Additional check: the negation should not be part of a positive phrase
                # e.g., "不是不..." (double negative) or "没有不..."
                # We skip if there's another negation before this one
                neg_idx = context.find(neg_word)
                before_neg = context[max(0, neg_idx - 5):neg_idx]
                if not any(n in before_neg for n in STRICT_NEGATIVE_PATTERNS):
                    return True

        # Check for strict negative patterns (must be immediately adjacent)
        for neg_word in STRICT_NEGATIVE_PATTERNS:
            # Only check within 3 characters before keyword
            strict_window = answer_lower[max(0, idx - 3):idx]
            if neg_word in strict_window:
                # Avoid false positives like "不错" (not bad = good)
                # If keyword starts with a positive character, it's likely not negation
                if idx < len(answer_lower):
                    next_char = answer_lower[idx] if idx < len(answer_lower) else ""
                    # Common positive words after "不": 不错, 不容易, 不简单
                    if next_char in "错容易简单多差":
                        continue
                    return True

        start = idx + 1

    return False


def _check_partial_coverage(answer: str, text: str) -> bool:
    """Check if the answer only partially covers the expected text.

    Returns True if partial coverage indicators are present.
    """
    answer_lower = answer.lower()

    for partial_word in PARTIAL_PATTERNS:
        if partial_word in answer_lower:
            return True

    # Check if answer is much shorter than expected text (suggests incomplete)
    if len(answer) < len(text) * 0.4:
        return True

    return False


def _enhanced_keyword_score(
    answer: str,
    text: str,
    keywords: list[str],
) -> tuple[float, list[str], bool]:
    """Enhanced keyword scoring with negative pattern detection.

    Returns:
        (score, hit_keywords, has_negative)
    """
    answer_clean = clean_text(answer).lower()
    text_clean = clean_text(text).lower()

    # Clean keywords
    clean_keywords = [clean_text(str(k)).lower() for k in keywords if str(k).strip()]

    hits = []
    has_negative = False

    for kw in clean_keywords:
        if not kw:
            continue

        if kw in answer_clean:
            # Check if this keyword hit is negated
            if _check_negative_context(answer_clean, kw):
                has_negative = True
                # Don't count negated keywords
                continue
            hits.append(kw)

    if not clean_keywords:
        return 0.0, [], False

    kw_score = len(hits) / len(clean_keywords)

    # Bonus for direct text overlap (beyond keywords)
    if text_clean and text_clean in answer_clean:
        kw_score = min(kw_score + 0.2, 1.0)

    return round(kw_score, 4), hits, has_negative


@dataclass
class DimensionCoverage:
    dimension_id: str
    text: str
    score: float
    covered: bool
    keyword_hits: list[str]
    negative: bool = False  # True if keyword hit but negated
    partial: bool = False  # True if partially covered
    confidence: float = 0.5  # Coverage confidence level

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "text": self.text,
            "score": self.score,
            "covered": self.covered,
            "keyword_hits": self.keyword_hits,
            "negative": self.negative,
            "partial": self.partial,
            "confidence": self.confidence,
        }


def evaluate_coverage(
    dimensions: list[dict[str, Any]],
    answer: str,
    adapter: EmbeddingAdapter | None = None,
    threshold: float = 0.35,  # Lowered from 0.5 to be more lenient
    kw_weight: float = 0.4,
    sem_weight: float = 0.6,
    enable_negative_detection: bool = True,
) -> dict[str, Any]:
    """Score how well `answer` covers each expected `dimension`.

    Each dimension: {"id": str, "text": str, "keywords": list[str]}.
    Coverage per dimension = kw_weight * keyword_hit_rate + sem_weight * cosine.
    Used by the tutor side against criterion.must_points.

    Args:
        dimensions: List of must-point dimensions
        answer: Employee's answer text
        adapter: Embedding adapter for semantic similarity
        threshold: Coverage threshold (default 0.35, lowered from 0.5)
        kw_weight: Weight for keyword matching (default 0.4)
        sem_weight: Weight for semantic similarity (default 0.6)
        enable_negative_detection: Enable negative pattern detection (default True)

    Returns:
        Dict with covered/missing dimension IDs and detailed scores
    """
    answer_clean = clean_text(answer)
    answer_embedding = adapter.embed_query(answer_clean) if (adapter is not None and answer_clean) else None

    items: list[DimensionCoverage] = []
    for dim in dimensions:
        text = clean_text(str(dim.get("text", "")))
        keywords = [clean_text(str(k)) for k in (dim.get("keywords") or []) if str(k).strip()]

        # Enhanced keyword scoring with negative detection
        if enable_negative_detection:
            kw_score, hits, has_negative = _enhanced_keyword_score(answer, text, keywords)
        else:
            # Legacy behavior
            hits = [k for k in keywords if k and k in answer_clean]
            kw_score = len(hits) / len(keywords) if keywords else 0.0
            has_negative = False

        # Semantic similarity
        sem_score = 0.0
        if answer_embedding is not None and text:
            sem_score = max(0.0, _cosine(answer_embedding, adapter.embed_query(text)))

        # Combined score
        raw_score = kw_weight * kw_score + sem_weight * sem_score

        # Apply penalty for negative context
        if has_negative:
            raw_score *= 0.3  # Heavy penalty for negated mentions

        score = round(raw_score, 4)

        # Check for partial coverage
        is_partial = _check_partial_coverage(answer_clean, text) if hits else False

        # Confidence level based on score strength
        if score >= 0.8:
            confidence = 0.9
        elif score >= 0.6:
            confidence = 0.7
        elif score >= 0.4:
            confidence = 0.5
        else:
            confidence = 0.3

        items.append(
            DimensionCoverage(
                dimension_id=str(dim.get("id", "")),
                text=str(dim.get("text", "")),
                score=score,
                covered=score >= threshold and not has_negative,
                keyword_hits=hits,
                negative=has_negative,
                partial=is_partial,
                confidence=round(confidence, 2),
            )
        )

    covered = [item.dimension_id for item in items if item.covered]
    missing = [item.dimension_id for item in items if not item.covered]

    # Additional breakdown for analysis
    negative_hits = [item.dimension_id for item in items if item.negative]
    partial_hits = [item.dimension_id for item in items if item.partial]

    return {
        "items": [item.to_dict() for item in items],
        "covered": covered,
        "missing": missing,
        "missing_texts": [item.text for item in items if not item.covered],
        "coverage_rate": round(len(covered) / max(len(items), 1), 4),
        "threshold": threshold,
        "negative_hits": negative_hits,
        "partial_hits": partial_hits,
        "negative_detection_enabled": enable_negative_detection,
    }


def compute_intent_gap(
    expected_intents: list[str],
    covered_intents: list[str],
) -> list[str]:
    """Set difference: expected customer concerns minus what was addressed.

    Used by the customer side. `covered_intents` is the cumulative set of intents
    the employee has addressed across the whole dialogue so far.
    """
    covered = set(covered_intents)
    return [intent for intent in expected_intents if intent not in covered]


def update_covered_intents(
    previous_covered: list[str],
    intent_scores: dict[str, float],
    threshold: float = 0.10,
) -> list[str]:
    """Accumulate addressed intents across turns.

    An intent counts as addressed once the employee answer scores above a small
    threshold for it (i.e. they actually talked about that topic this turn).

    Default 0.10 calibrated via eval/sweep on 104-row gap gold set
    (accuracy 0.9481 at 0.05-0.12; was 0.36 → accuracy only 0.6651).
    """
    covered = set(previous_covered)
    for intent, score in intent_scores.items():
        if score >= threshold:
            covered.add(intent)
    return sorted(covered)
