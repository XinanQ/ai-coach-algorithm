"""Shared metrics for the RAG evaluation framework.

Re-exports multilabel_prf1 from the production code and adds retrieval /
coverage metrics used by multiple stage evaluators.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.intent_metrics import multilabel_prf1  # noqa: F401


@dataclass
class StageResult:
    stage: str
    primary_metric: str
    value: float
    gold_size: int
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "primary_metric": self.primary_metric,
            "value": round(self.value, 4),
            "gold_size": self.gold_size,
            "details": self.details,
        }


def recall_at_k(gold_ids: list[str], pred_ids: list[str], k: int = 3) -> float:
    pred_set = set(pred_ids[:k])
    if not gold_ids:
        return 1.0
    return sum(1 for g in gold_ids if g in pred_set) / len(gold_ids)


def precision_at_k(gold_ids: list[str], pred_ids: list[str], k: int = 3) -> float:
    top_k = pred_ids[:k]
    if not top_k:
        return 0.0
    gold_set = set(gold_ids)
    return sum(1 for p in top_k if p in gold_set) / len(top_k)


def mrr(gold_ids: list[str], pred_ids: list[str]) -> float:
    gold_set = set(gold_ids)
    for rank, pid in enumerate(pred_ids, 1):
        if pid in gold_set:
            return 1.0 / rank
    return 0.0


def point_level_prf1(
    gold_covered: set[str],
    gold_missing: set[str],
    pred_covered: set[str],
    pred_missing: set[str],
) -> dict[str, float]:
    all_points = gold_covered | gold_missing
    tp = len(gold_covered & pred_covered)
    fp = len(pred_covered - gold_covered)
    fn = len(gold_covered - pred_covered)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    accuracy = sum(1 for p in all_points if (p in gold_covered) == (p in pred_covered)) / max(len(all_points), 1)
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }
