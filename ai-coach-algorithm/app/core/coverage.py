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
from dataclasses import dataclass
from typing import Any

from app.core.embedding_adapter import EmbeddingAdapter
from app.core.text_cleaner import clean_text


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class DimensionCoverage:
    dimension_id: str
    text: str
    score: float
    covered: bool
    keyword_hits: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "text": self.text,
            "score": self.score,
            "covered": self.covered,
            "keyword_hits": self.keyword_hits,
        }


def evaluate_coverage(
    dimensions: list[dict[str, Any]],
    answer: str,
    adapter: EmbeddingAdapter | None = None,
    threshold: float = 0.5,
    kw_weight: float = 0.4,
    sem_weight: float = 0.6,
) -> dict[str, Any]:
    """Score how well `answer` covers each expected `dimension`.

    Each dimension: {"id": str, "text": str, "keywords": list[str]}.
    Coverage per dimension = kw_weight * keyword_hit_rate + sem_weight * cosine.
    Used by the tutor side against criterion.must_points.
    """
    answer_clean = clean_text(answer)
    answer_embedding = adapter.embed_query(answer_clean) if (adapter is not None and answer_clean) else None

    items: list[DimensionCoverage] = []
    for dim in dimensions:
        text = clean_text(str(dim.get("text", "")))
        keywords = [clean_text(str(k)) for k in (dim.get("keywords") or []) if str(k).strip()]
        hits = [k for k in keywords if k and k in answer_clean]
        kw_score = len(hits) / len(keywords) if keywords else 0.0
        sem_score = 0.0
        if answer_embedding is not None and text:
            sem_score = max(0.0, _cosine(answer_embedding, adapter.embed_query(text)))
        score = round(kw_weight * kw_score + sem_weight * sem_score, 4)
        items.append(
            DimensionCoverage(
                dimension_id=str(dim.get("id", "")),
                text=str(dim.get("text", "")),
                score=score,
                covered=score >= threshold,
                keyword_hits=hits,
            )
        )

    covered = [item.dimension_id for item in items if item.covered]
    missing = [item.dimension_id for item in items if not item.covered]
    return {
        "items": [item.to_dict() for item in items],
        "covered": covered,
        "missing": missing,
        "missing_texts": [item.text for item in items if not item.covered],
        "coverage_rate": round(len(covered) / max(len(items), 1), 4),
        "threshold": threshold,
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
