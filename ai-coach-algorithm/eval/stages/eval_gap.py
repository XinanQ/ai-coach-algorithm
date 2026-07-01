"""Stage 2: Gap computation evaluation.

Runs analyze_customer_answer → update_covered_intents on each gold row,
compares predicted covered/missing intents against gold labels.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.coverage import update_covered_intents
from app.core.customer_answer_understanding import analyze_customer_answer
from eval.metrics import StageResult

GOLD_PATH = Path("data/eval/gap_computation_gold.jsonl")


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
    threshold: float = 0.10,
    gold_path: Path = GOLD_PATH,
    verbose: bool = False,
) -> StageResult:
    rows = load_gold(gold_path)

    correct = 0
    total_intents = 0
    false_covered = 0
    false_missing = 0
    errors: list[dict[str, Any]] = []

    for row in rows:
        understanding = analyze_customer_answer(row["employee_answer"])
        intent_scores = understanding.get("intent_scores", {})
        pred_covered = set(update_covered_intents([], intent_scores, threshold=threshold))

        expected = set(row["expected_intents"])
        gold_covered = set(row["gold_covered"])
        gold_missing = set(row["gold_missing"])

        for intent in expected:
            total_intents += 1
            in_gold_covered = intent in gold_covered
            in_pred_covered = intent in pred_covered
            if in_gold_covered == in_pred_covered:
                correct += 1
            elif in_pred_covered and not in_gold_covered:
                false_covered += 1
            else:
                false_missing += 1

        if verbose:
            if pred_covered & expected != gold_covered & expected:
                errors.append({
                    "id": row["id"],
                    "answer": row["employee_answer"][:60],
                    "gold_covered": sorted(gold_covered),
                    "pred_covered": sorted(pred_covered & expected),
                    "scores": {k: round(v, 3) for k, v in sorted(intent_scores.items(), key=lambda x: -x[1])},
                })

    accuracy = correct / max(total_intents, 1)
    false_covered_rate = false_covered / max(total_intents, 1)
    false_missing_rate = false_missing / max(total_intents, 1)

    details: dict[str, Any] = {
        "params": {"threshold": threshold},
        "accuracy": round(accuracy, 4),
        "false_covered_rate": round(false_covered_rate, 4),
        "false_missing_rate": round(false_missing_rate, 4),
        "total_intents_evaluated": total_intents,
    }
    if verbose:
        details["errors"] = errors[:30]

    return StageResult(
        stage="gap_computation",
        primary_metric="accuracy",
        value=round(accuracy, 4),
        gold_size=len(rows),
        details=details,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate gap computation stage.")
    parser.add_argument("--threshold", type=float, default=0.10)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = evaluate(threshold=args.threshold, verbose=args.verbose)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
