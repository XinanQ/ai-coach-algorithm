"""Multi-label intent metrics shared by the calibrator and model eval."""
from __future__ import annotations

from typing import Iterable

from app.core.intent_labels import INTENT_LABELS


def _f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    return round(precision, 4), round(recall, 4), round(f1, 4)


def multilabel_prf1(
    gold_sets: list[set[str]],
    pred_sets: list[set[str]],
    labels: Iterable[str] = tuple(INTENT_LABELS),
) -> dict[str, object]:
    """Micro + macro precision/recall/F1 over multi-label predictions."""
    labels = list(labels)
    micro_tp = micro_fp = micro_fn = 0
    per_label: dict[str, dict[str, float]] = {}
    macro_f1_values: list[float] = []

    for label in labels:
        tp = sum(1 for g, p in zip(gold_sets, pred_sets) if label in g and label in p)
        fp = sum(1 for g, p in zip(gold_sets, pred_sets) if label not in g and label in p)
        fn = sum(1 for g, p in zip(gold_sets, pred_sets) if label in g and label not in p)
        micro_tp += tp
        micro_fp += fp
        micro_fn += fn
        precision, recall, f1 = _f1(tp, fp, fn)
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}
        macro_f1_values.append(f1)

    micro_p, micro_r, micro_f1 = _f1(micro_tp, micro_fp, micro_fn)
    return {
        "micro_precision": micro_p,
        "micro_recall": micro_r,
        "micro_f1": micro_f1,
        "macro_f1": round(sum(macro_f1_values) / max(len(macro_f1_values), 1), 4),
        "per_label": per_label,
    }
