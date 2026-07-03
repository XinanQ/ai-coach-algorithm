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


def ceiling_at_k(gold_ids: list[str], k: int) -> float:
    """Calculate the mathematical ceiling for recall@k.

    The ceiling is the maximum possible recall given k and the number of gold items.
    If gold has N items, the max we can retrieve is min(k, N), so ceiling = min(k, N) / N.

    This explains why recall@3 can never reach 1.0 when gold has >3 items.
    """
    if not gold_ids:
        return 1.0
    return min(k, len(gold_ids)) / len(gold_ids)


def normalized_recall_at_k(gold_ids: list[str], pred_ids: list[str], k: int = 3) -> float:
    """Calculate recall@k normalized by the mathematical ceiling.

    This answers: "What fraction of the theoretical maximum did we achieve?"
    A value of 0.8 means we got 80% of what was mathematically possible.

    Useful when gold sets vary widely in size (e.g., 3 vs 12 gold chunks).
    """
    recall = recall_at_k(gold_ids, pred_ids, k)
    ceiling = ceiling_at_k(gold_ids, k)
    return recall / max(ceiling, 1e-8)


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
