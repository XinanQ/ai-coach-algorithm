"""Stage 3: Chunk retrieval evaluation.

Runs retrieve_marketing_knowledge on each gold row, compares returned
chunk_ids against gold_chunk_ids, reports Recall@K, MRR, Precision@K.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.marketing_rag import retrieve_marketing_knowledge
from eval.metrics import StageResult, mrr, precision_at_k, recall_at_k

GOLD_PATH = Path("data/eval/retrieval_gold.jsonl")


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
    top_k: int = 3,
    fusion_weights: dict[str, float] | None = None,
    gold_path: Path = GOLD_PATH,
    route_filter: str | None = None,
    verbose: bool = False,
) -> StageResult:
    rows = load_gold(gold_path)
    if route_filter:
        rows = [r for r in rows if r["route"] == route_filter]

    recall_scores: list[float] = []
    mrr_scores: list[float] = []
    precision_scores: list[float] = []
    errors: list[dict[str, Any]] = []

    for row in rows:
        try:
            result = retrieve_marketing_knowledge(
                query=row["query"],
                route=row["route"],
                top_k=top_k,
                scene_id=row.get("scene_id"),
                fusion_weights=fusion_weights,
            )
            pred_ids = [item.get("chunk_id", item.get("id", "")) for item in result.get("items", [])]
        except Exception as exc:
            pred_ids = []
            if verbose:
                errors.append({"id": row["id"], "error": str(exc)})

        gold_ids = row["gold_chunk_ids"]
        recall_scores.append(recall_at_k(gold_ids, pred_ids, k=top_k))
        mrr_scores.append(mrr(gold_ids, pred_ids))
        precision_scores.append(precision_at_k(gold_ids, pred_ids, k=top_k))

        if verbose and recall_at_k(gold_ids, pred_ids, k=top_k) < 1.0:
            errors.append({
                "id": row["id"],
                "route": row["route"],
                "gold": gold_ids,
                "pred": pred_ids[:top_k],
                "recall": round(recall_at_k(gold_ids, pred_ids, k=top_k), 3),
            })

    avg_recall = sum(recall_scores) / max(len(recall_scores), 1)
    avg_mrr = sum(mrr_scores) / max(len(mrr_scores), 1)
    avg_precision = sum(precision_scores) / max(len(precision_scores), 1)

    by_route: dict[str, dict[str, float]] = {}
    for row, rec, mr, prec in zip(rows, recall_scores, mrr_scores, precision_scores):
        rt = row["route"]
        if rt not in by_route:
            by_route[rt] = {"recall_sum": 0, "mrr_sum": 0, "prec_sum": 0, "count": 0}
        by_route[rt]["recall_sum"] += rec
        by_route[rt]["mrr_sum"] += mr
        by_route[rt]["prec_sum"] += prec
        by_route[rt]["count"] += 1
    route_metrics = {
        rt: {
            f"recall@{top_k}": round(d["recall_sum"] / max(d["count"], 1), 4),
            "mrr": round(d["mrr_sum"] / max(d["count"], 1), 4),
            f"precision@{top_k}": round(d["prec_sum"] / max(d["count"], 1), 4),
            "count": d["count"],
        }
        for rt, d in by_route.items()
    }

    details: dict[str, Any] = {
        "params": {"top_k": top_k, "fusion_weights": fusion_weights},
        f"recall@{top_k}": round(avg_recall, 4),
        "mrr": round(avg_mrr, 4),
        f"precision@{top_k}": round(avg_precision, 4),
        "by_route": route_metrics,
    }
    if verbose:
        details["errors"] = errors[:30]

    return StageResult(
        stage="chunk_retrieval",
        primary_metric=f"recall@{top_k}",
        value=round(avg_recall, 4),
        gold_size=len(rows),
        details=details,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate chunk retrieval stage.")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--route", choices=["tutor", "customer"])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    result = evaluate(top_k=args.top_k, route_filter=args.route, verbose=args.verbose)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
