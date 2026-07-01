"""Parameter sweep for any evaluation stage.

Usage:
    python -m eval.sweep --stage intent --param kw_weight --min 0.3 --max 0.8 --steps 11
    python -m eval.sweep --stage intent --grid '{"kw_weight": [0.4, 0.5, 0.6], "abs_floor": [0.15, 0.20, 0.25]}'
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from io import StringIO
from typing import Any

from eval.stages.eval_intent import evaluate as eval_intent
from eval.stages.eval_gap import evaluate as eval_gap
from eval.stages.eval_must_point import evaluate as eval_must_point


STAGE_RUNNERS = {
    "intent": eval_intent,
    "gap": eval_gap,
    "must_point": eval_must_point,
}

STAGE_PARAM_KEYS = {
    "intent": ["kw_weight", "sem_weight", "abs_floor", "rel_ratio"],
    "gap": ["threshold"],
    "must_point": ["threshold", "kw_weight", "sem_weight"],
}


def _single_param_sweep(
    stage: str,
    param: str,
    min_val: float,
    max_val: float,
    steps: int,
) -> list[dict[str, Any]]:
    runner = STAGE_RUNNERS[stage]
    results = []
    for i in range(steps):
        val = round(min_val + (max_val - min_val) * i / max(steps - 1, 1), 4)
        kwargs = {param: val}
        if param == "kw_weight":
            kwargs["sem_weight"] = round(1.0 - val, 4)
        result = runner(**kwargs)
        row = {"param": param, param: val, "primary": result.value}
        row.update({k: v for k, v in result.details.items() if isinstance(v, (int, float))})
        results.append(row)
    return results


def _grid_sweep(stage: str, grid: dict[str, list[float]]) -> list[dict[str, Any]]:
    runner = STAGE_RUNNERS[stage]
    keys = list(grid.keys())
    combos = list(itertools.product(*[grid[k] for k in keys]))
    results = []
    for combo in combos:
        kwargs = dict(zip(keys, combo))
        if "kw_weight" in kwargs and "sem_weight" not in kwargs:
            kwargs["sem_weight"] = round(1.0 - kwargs["kw_weight"], 4)
        result = runner(**kwargs)
        row = {**kwargs, "primary": result.value}
        row.update({k: v for k, v in result.details.items() if isinstance(v, (int, float))})
        results.append(row)
    return results


def format_csv(results: list[dict[str, Any]]) -> str:
    if not results:
        return ""
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(results[0].keys()))
    writer.writeheader()
    writer.writerows(results)
    return buf.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description="Parameter sweep for RAG evaluation stages.")
    parser.add_argument("--stage", required=True, choices=list(STAGE_RUNNERS.keys()))
    parser.add_argument("--param", help="Single parameter to sweep")
    parser.add_argument("--min", type=float, default=0.0)
    parser.add_argument("--max", type=float, default=1.0)
    parser.add_argument("--steps", type=int, default=11)
    parser.add_argument("--grid", help="JSON dict of param → values for grid sweep")
    parser.add_argument("--output", help="CSV output path")
    args = parser.parse_args()

    if args.grid:
        grid = json.loads(args.grid)
        results = _grid_sweep(args.stage, grid)
    elif args.param:
        results = _single_param_sweep(args.stage, args.param, args.min, args.max, args.steps)
    else:
        parser.error("Specify --param or --grid")
        return

    csv_text = format_csv(results)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(csv_text)
        print(f"Saved {len(results)} rows to {args.output}")
    else:
        print(csv_text)

    best = max(results, key=lambda r: r["primary"])
    print(f"\nBest: primary={best['primary']:.4f}", end="")
    for k, v in best.items():
        if k != "primary" and isinstance(v, float):
            print(f"  {k}={v:.4f}", end="")
    print()


if __name__ == "__main__":
    main()
