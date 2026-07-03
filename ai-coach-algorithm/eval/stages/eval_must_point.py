"""Stage 4: Must-point coverage evaluation.

Runs evaluate_coverage on each gold row, compares predicted covered/missing
must_points against gold labels, reports point-level P/R/F1.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.coverage import evaluate_coverage
from app.core.embedding_adapter import get_embedding_adapter
from eval.metrics import StageResult, point_level_prf1

GOLD_PATH = Path("data/eval/must_point_coverage_gold.jsonl")


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
    threshold: float = 0.60,
    kw_weight: float = 0.25,
    sem_weight: float = 0.75,
    gold_path: Path = GOLD_PATH,
    verbose: bool = False,
) -> StageResult:
    rows = load_gold(gold_path)
    adapter = get_embedding_adapter()

    all_tp = all_fp = all_fn = 0
    coverage_ae: list[float] = []
    errors: list[dict[str, Any]] = []

    for row in rows:
        must_points = row["must_points"]
        key_terms = row.get("key_terms", [])
        dimensions = [
            {"id": f"mp_{i}", "text": mp, "keywords": key_terms}
            for i, mp in enumerate(must_points)
        ]

        result = evaluate_coverage(
            dimensions, row["employee_answer"], adapter,
            threshold=threshold, kw_weight=kw_weight, sem_weight=sem_weight,
        )

        pred_covered_idx = set(result["covered"])
        pred_missing_idx = set(result["missing"])

        gold_covered_set = set(row["gold_covered_points"])
        gold_covered_idx = set()
        gold_missing_idx = set()
        for i, mp in enumerate(must_points):
            idx = f"mp_{i}"
            if mp in gold_covered_set:
                gold_covered_idx.add(idx)
            else:
                gold_missing_idx.add(idx)

        prf1 = point_level_prf1(gold_covered_idx, gold_missing_idx, pred_covered_idx, pred_missing_idx)
        all_tp += len(gold_covered_idx & pred_covered_idx)
        all_fp += len(pred_covered_idx - gold_covered_idx)
        all_fn += len(gold_covered_idx - pred_covered_idx)

        gold_rate = len(gold_covered_idx) / max(len(must_points), 1)
        pred_rate = result["coverage_rate"]
        coverage_ae.append(abs(gold_rate - pred_rate))

        if verbose and prf1["f1"] < 1.0:
            errors.append({
                "id": row["id"],
                "quality": row.get("quality"),
                "gold_covered": sorted(gold_covered_idx),
                "pred_covered": sorted(pred_covered_idx),
                "point_f1": prf1["f1"],
            })

    precision = all_tp / max(all_tp + all_fp, 1)
    recall = all_tp / max(all_tp + all_fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-8)
    mae = sum(coverage_ae) / max(len(coverage_ae), 1)

    # Enhanced error analysis by quality
    quality_stats = {}
    if verbose:
        by_quality: dict[str, list[dict]] = {"good": [], "partial": [], "poor": []}
        for err in errors:
            quality = err.get("quality", "unknown")
            if quality in by_quality:
                by_quality[quality].append(err)

        for qual, errs in by_quality.items():
            if errs:
                avg_f1 = sum(e["point_f1"] for e in errs) / len(errs)
                quality_stats[f"{qual}_count"] = len(errs)
                quality_stats[f"{qual}_avg_f1"] = round(avg_f1, 4)

    details: dict[str, Any] = {
        "params": {"threshold": threshold, "kw_weight": kw_weight, "sem_weight": sem_weight},
        "point_precision": round(precision, 4),
        "point_recall": round(recall, 4),
        "point_f1": round(f1, 4),
        "coverage_rate_mae": round(mae, 4),
    }
    if verbose:
        details["errors"] = errors[:30]
        details["quality_stats"] = quality_stats

    return StageResult(
        stage="must_point_coverage",
        primary_metric="point_f1",
        value=round(f1, 4),
        gold_size=len(rows),
        details=details,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate must-point coverage stage.")
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument("--kw-weight", type=float, default=0.25)
    parser.add_argument("--sem-weight", type=float, default=0.75)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--save-verbose", action="store_true", help="Save verbose errors to file")
    args = parser.parse_args()

    result = evaluate(
        threshold=args.threshold,
        kw_weight=args.kw_weight,
        sem_weight=args.sem_weight,
        verbose=args.verbose,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if args.save_verbose and args.verbose and "errors" in result.details:
        verbose_path = f"data/eval/must_point_verbose_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(verbose_path, "w", encoding="utf-8") as f:
            json.dump({"stage": "must_point_coverage", "details": result.details}, f, ensure_ascii=False, indent=2)
        print(f"\nVerbose errors saved to {verbose_path}")


if __name__ == "__main__":
    main()
