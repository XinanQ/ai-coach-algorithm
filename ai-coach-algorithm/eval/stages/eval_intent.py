"""Stage 1: Intent detection evaluation.

Runs _build_customer_query_plan → _select_intent_labels on each gold row,
compares predicted labels against gold_labels, reports P/R/F1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.core.embedding_adapter import get_embedding_adapter
from app.core.intent_labels import INTENT_LABELS
from app.core.marketing_rag import (
    INTENT_ABS_FLOOR,
    INTENT_MAX_LABELS,
    INTENT_REL_RATIO,
    _build_customer_query_plan,
    _intent_semantic_scores,
    _select_intent_labels,
)
from eval.metrics import StageResult, multilabel_prf1

GOLD_PATH = Path("data/intent_eval_gold.jsonl")


def load_gold(path: Path = GOLD_PATH) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def evaluate(
    *,
    kw_weight: float = 0.55,
    sem_weight: float = 0.45,
    abs_floor: float = INTENT_ABS_FLOOR,
    rel_ratio: float = INTENT_REL_RATIO,
    max_labels: int = INTENT_MAX_LABELS,
    gold_path: Path = GOLD_PATH,
    verbose: bool = False,
) -> StageResult:
    rows = load_gold(gold_path)
    adapter = get_embedding_adapter()

    gold_sets: list[set[str]] = []
    pred_sets: list[set[str]] = []
    errors: list[dict[str, Any]] = []

    for row in rows:
        gold_labels = set(row.get("gold_labels") or [])
        gold_sets.append(gold_labels)

        plan = _build_customer_query_plan(
            row["text"], adapter, kw_weight=kw_weight, sem_weight=sem_weight
        )
        fused = plan["fused_intent_scores"]

        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
        top_score = ranked[0][1] if ranked else 0.0
        cutoff = max(abs_floor, rel_ratio * top_score)
        predicted = set(label for label, score in ranked if score >= cutoff)
        if len(predicted) > max_labels:
            predicted = set(list(predicted)[:max_labels])

        pred_sets.append(predicted)

        if verbose and predicted != gold_labels:
            errors.append({
                "id": row.get("id"),
                "text": row["text"][:60],
                "gold": sorted(gold_labels),
                "pred": sorted(predicted),
                "fused_scores": {k: round(v, 3) for k, v in sorted(fused.items(), key=lambda x: -x[1])},
            })

    metrics = multilabel_prf1(gold_sets, pred_sets, labels=INTENT_LABELS)

    details: dict[str, Any] = {
        "params": {
            "kw_weight": kw_weight,
            "sem_weight": sem_weight,
            "abs_floor": abs_floor,
            "rel_ratio": rel_ratio,
            "max_labels": max_labels,
        },
        "micro_precision": metrics["micro_precision"],
        "micro_recall": metrics["micro_recall"],
        "micro_f1": metrics["micro_f1"],
        "macro_f1": metrics["macro_f1"],
        "per_label": metrics["per_label"],
    }
    if verbose:
        details["errors"] = errors[:30]

    return StageResult(
        stage="intent_detection",
        primary_metric="micro_f1",
        value=metrics["micro_f1"],
        gold_size=len(rows),
        details=details,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate intent detection stage.")
    parser.add_argument("--kw-weight", type=float, default=0.55)
    parser.add_argument("--sem-weight", type=float, default=0.45)
    parser.add_argument("--abs-floor", type=float, default=INTENT_ABS_FLOOR)
    parser.add_argument("--rel-ratio", type=float, default=INTENT_REL_RATIO)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = evaluate(
        kw_weight=args.kw_weight,
        sem_weight=args.sem_weight,
        abs_floor=args.abs_floor,
        rel_ratio=args.rel_ratio,
        verbose=args.verbose,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
