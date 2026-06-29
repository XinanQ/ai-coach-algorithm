"""Calibrate the intent presence threshold against labeled data.

The customer-side coverage logic (`update_covered_intents`, default 0.05) and the
retrieval label gate decide "is intent X present" by thresholding a per-label
score. This sweeps that threshold against gold labels and reports the value that
maximizes micro-F1, so the threshold is data-driven instead of guessed.

Runs now with placeholder labels; numbers are only meaningful once gold exists.
"""
from __future__ import annotations

import argparse
import json

from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.intent_dataset_prep import DEFAULT_INPUT, load_labeled_rows
from app.core.intent_labels import INTENT_LABELS
from app.core.intent_metrics import multilabel_prf1


def _score_rows(rows: list[dict[str, object]]) -> list[tuple[set[str], dict[str, float]]]:
    scored: list[tuple[set[str], dict[str, float]]] = []
    for row in rows:
        understanding = analyze_customer_answer(str(row["text"]))
        scores = {label: float(understanding["intent_scores"].get(label, 0.0)) for label in INTENT_LABELS}
        scored.append((set(row["labels"]), scores))
    return scored


def calibrate(rows: list[dict[str, object]], steps: int = 41) -> dict[str, object]:
    scored = _score_rows(rows)
    sweep = []
    best = {"threshold": 0.0, "micro_f1": -1.0}
    for i in range(steps):
        threshold = round(i / (steps - 1) * 0.8, 4)  # sweep 0.0 .. 0.8
        gold_sets = [gold for gold, _ in scored]
        pred_sets = [{label for label, score in scores.items() if score >= threshold} for _, scores in scored]
        metrics = multilabel_prf1(gold_sets, pred_sets)
        sweep.append({"threshold": threshold, "micro_f1": metrics["micro_f1"], "macro_f1": metrics["macro_f1"]})
        if metrics["micro_f1"] > best["micro_f1"]:
            best = {"threshold": threshold, **{k: metrics[k] for k in ("micro_precision", "micro_recall", "micro_f1", "macro_f1")}}
    return {"best": best, "sweep": sweep}


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate intent presence threshold from labeled data.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--steps", type=int, default=41)
    args = parser.parse_args()

    rows = load_labeled_rows(args.input)
    gold_count = sum(1 for r in rows if r["is_gold"])
    result = calibrate(rows, steps=args.steps)
    result["rows"] = len(rows)
    result["gold_reviewed"] = gold_count
    if not gold_count:
        result["warning"] = "No reviewed gold — calibration ran on PLACEHOLDER labels (self-consistent with keyword suggestions). Re-run after annotation."
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
