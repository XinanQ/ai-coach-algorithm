"""Stage 3: Chunk retrieval evaluation with two-stage architecture.

Runs retrieve_marketing_knowledge with eval_mode=True to get:
1. Candidate recall@10/20 - whether we can find gold in the candidate pool
2. Reranked recall@3/top5 - whether reranking can bring gold to the front
3. Ceiling metrics - what's mathematically possible given gold set size
4. Normalized recall - performance relative to ceiling
5. Error analysis distinguishing candidate miss from rerank miss
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.chroma_vector_store import MAX_QUERY_RESULTS
from app.core.marketing_rag import retrieve_marketing_knowledge
from eval.metrics import (
    StageResult,
    ceiling_at_k,
    mrr,
    normalized_recall_at_k,
    precision_at_k,
    recall_at_k,
)

GOLD_PATH = Path("data/eval/retrieval_gold.jsonl")


def load_gold(path: Path = GOLD_PATH) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _extract_chunk_id(item_id: str) -> str:
    """Extract pure chunk ID from Chroma ID format 'route:MCH_XXX' or 'MCH_XXX'."""
    if ":" in str(item_id):
        return str(item_id).split(":", 1)[1]
    return str(item_id)


def _get_ids_from_items(items: list[dict[str, Any]]) -> list[str]:
    """Extract chunk IDs from retrieval items."""
    return [
        _extract_chunk_id(item.get("chunk_id") or item.get("id") or item.get("metadata", {}).get("chunk_id", ""))
        for item in items
    ]


def evaluate(
    *,
    candidate_k: int = 20,
    final_k: int = 3,
    fusion_weights: dict[str, float] | None = None,
    gold_path: Path = GOLD_PATH,
    route_filter: str | None = None,
    verbose: bool = False,
) -> StageResult:
    """Evaluate two-stage retrieval: candidate pool → rerank → final topN.

    Args:
        candidate_k: Size of candidate pool (default 20)
        final_k: Final number of chunks to return to LLM (default 3)
        fusion_weights: Override fusion weights for retrieval
        gold_path: Path to gold data
        route_filter: Filter by route ("tutor" or "customer")
        verbose: Include detailed error analysis

    Returns:
        StageResult with two-stage metrics
    """
    rows = load_gold(gold_path)
    if route_filter:
        rows = [r for r in rows if r["route"] == route_filter]

    # Track metrics at different stages
    candidate_recall_10: list[float] = []
    candidate_recall_20: list[float] = []
    reranked_recall_3: list[float] = []
    reranked_recall_5: list[float] = []
    reranked_recall_8: list[float] = []
    reranked_recall_10: list[float] = []
    context_hit_5: list[float] = []
    context_hit_8: list[float] = []
    precision_3: list[float] = []
    precision_5: list[float] = []
    precision_8: list[float] = []
    final_context_recall: list[float] = []
    final_context_precision: list[float] = []
    final_context_hit: list[float] = []
    mrr_scores: list[float] = []
    ceiling_3: list[float] = []
    ceiling_10: list[float] = []
    ceiling_20: list[float] = []
    normalized_candidate_recall_10: list[float] = []
    normalized_candidate_recall_20: list[float] = []
    normalized_reranked_recall_3: list[float] = []
    normalized_reranked_recall_5: list[float] = []
    normalized_reranked_recall_8: list[float] = []
    normalized_context_hit_5: list[float] = []
    normalized_context_hit_8: list[float] = []

    errors: list[dict[str, Any]] = []

    for row in rows:
        try:
            # Request eval_mode to get candidate pool and reranked results
            result = retrieve_marketing_knowledge(
                query=row["query"],
                route=row["route"],
                final_k=final_k,
                candidate_k=candidate_k,
                scene_id=row.get("scene_id"),
                fusion_weights=fusion_weights,
                eval_mode=True,  # Enable eval mode to get candidate_items and reranked_items
            )

            # Extract IDs at each stage
            candidate_ids = _get_ids_from_items(result.get("candidate_items", []))
            reranked_ids = _get_ids_from_items(result.get("reranked_items", []))
            final_ids = _get_ids_from_items(result.get("items", []))

        except Exception as exc:
            candidate_ids = []
            reranked_ids = []
            final_ids = []
            if verbose:
                errors.append({
                    "id": row["id"],
                    "route": row.get("route"),
                    "scene_id": row.get("scene_id"),
                    "gold_count": len(row.get("gold_chunk_ids", [])),
                    "miss_type": "retrieval_error",
                    "error": str(exc),
                    "recall@3": 0.0,
                    "recall@10": 0.0,
                    "ceiling@3": ceiling_at_k(row.get("gold_chunk_ids", []), 3),
                })

        gold_ids = row["gold_chunk_ids"]
        gold_set = set(gold_ids)

        # Stage 1: Candidate pool metrics
        candidate_recall_10.append(recall_at_k(gold_ids, candidate_ids, k=10))
        candidate_recall_20.append(recall_at_k(gold_ids, candidate_ids, k=20))

        # Stage 2: Reranked/final metrics
        reranked_recall_3.append(recall_at_k(gold_ids, reranked_ids, k=3))
        reranked_recall_5.append(recall_at_k(gold_ids, reranked_ids, k=5))
        reranked_recall_8.append(recall_at_k(gold_ids, reranked_ids, k=8))
        reranked_recall_10.append(recall_at_k(gold_ids, reranked_ids, k=10))
        # Context hit: whether gold appears anywhere in top-k (not just at-k)
        context_hit_5.append(1.0 if any(g in reranked_ids[:5] for g in gold_set) else 0.0)
        context_hit_8.append(1.0 if any(g in reranked_ids[:8] for g in gold_set) else 0.0)
        precision_3.append(precision_at_k(gold_ids, reranked_ids, k=3))
        precision_5.append(precision_at_k(gold_ids, reranked_ids, k=5))
        precision_8.append(precision_at_k(gold_ids, reranked_ids, k=8))
        final_context_recall.append(recall_at_k(gold_ids, final_ids, k=final_k))
        final_context_precision.append(precision_at_k(gold_ids, final_ids, k=final_k))
        final_context_hit.append(1.0 if any(g in final_ids[:final_k] for g in gold_set) else 0.0)
        mrr_scores.append(mrr(gold_ids, reranked_ids))

        # Ceiling metrics - what's mathematically possible
        ceil_3 = ceiling_at_k(gold_ids, 3)
        ceil_10 = ceiling_at_k(gold_ids, 10)
        ceil_20 = ceiling_at_k(gold_ids, 20)
        ceiling_3.append(ceil_3)
        ceiling_10.append(ceil_10)
        ceiling_20.append(ceil_20)

        # Normalized metrics - performance relative to ceiling
        normalized_candidate_recall_10.append(normalized_recall_at_k(gold_ids, candidate_ids, k=10))
        normalized_candidate_recall_20.append(normalized_recall_at_k(gold_ids, candidate_ids, k=20))
        normalized_reranked_recall_3.append(normalized_recall_at_k(gold_ids, reranked_ids, k=3))
        normalized_reranked_recall_5.append(normalized_recall_at_k(gold_ids, reranked_ids, k=5))
        normalized_reranked_recall_8.append(normalized_recall_at_k(gold_ids, reranked_ids, k=8))
        # Normalized context hit
        norm_hit_5 = 1.0 if any(g in reranked_ids[:5] for g in gold_set) else 0.0
        norm_hit_8 = 1.0 if any(g in reranked_ids[:8] for g in gold_set) else 0.0
        normalized_context_hit_5.append(norm_hit_5)
        normalized_context_hit_8.append(norm_hit_8)

        # Error analysis: compare against the mathematical ceiling. A case with
        # 12 gold chunks and top3 returning 3 gold chunks is not a failure.
        if verbose and candidate_ids:
            gold_in_candidate_10 = any(g in candidate_ids[:10] for g in gold_set)
            gold_in_candidate_20 = any(g in candidate_ids[:20] for g in gold_set)
            gold_in_final = any(g in final_ids for g in gold_set)

            recall_3 = recall_at_k(gold_ids, final_ids, k=3)
            norm_candidate_10 = normalized_recall_at_k(gold_ids, candidate_ids, k=10)
            norm_candidate_20 = normalized_recall_at_k(gold_ids, candidate_ids, k=20)
            norm_reranked_3 = normalized_recall_at_k(gold_ids, reranked_ids, k=3)
            norm_reranked_5 = normalized_recall_at_k(gold_ids, reranked_ids, k=5)
            if norm_reranked_3 < 0.9999:
                if norm_candidate_20 < 0.9999:
                    miss_type = "candidate_miss"
                elif norm_candidate_10 < 0.9999:
                    miss_type = "recall_10_candidate_miss"
                else:
                    miss_type = "rerank_miss"

                errors.append({
                    "id": row["id"],
                    "route": row["route"],
                    "scene_id": row.get("scene_id"),
                    "gold": gold_ids,
                    "gold_count": len(gold_ids),
                    "candidate_top_10": candidate_ids[:10],
                    "candidate_top_20": candidate_ids[:20],
                    "reranked_top_10": reranked_ids[:10],
                    "final_top_k": final_ids[:final_k],
                    "gold_in_candidate_10": gold_in_candidate_10,
                    "gold_in_candidate_20": gold_in_candidate_20,
                    "gold_in_final": gold_in_final,
                    "miss_type": miss_type,
                    "recall@3": round(recall_3, 4),
                    "recall@10": round(candidate_recall_10[-1], 4),
                    "recall@20": round(candidate_recall_20[-1], 4),
                    "ceiling@3": round(ceil_3, 4),
                    "ceiling@10": round(ceil_10, 4),
                    "normalized_candidate_recall@10": round(norm_candidate_10, 4),
                    "normalized_candidate_recall@20": round(norm_candidate_20, 4),
                    "normalized_reranked_recall@3": round(norm_reranked_3, 4),
                    "normalized_reranked_recall@5": round(norm_reranked_5, 4),
                })

    # Compute averages
    avg_candidate_recall_10 = sum(candidate_recall_10) / max(len(candidate_recall_10), 1)
    avg_candidate_recall_20 = sum(candidate_recall_20) / max(len(candidate_recall_20), 1)
    avg_reranked_recall_3 = sum(reranked_recall_3) / max(len(reranked_recall_3), 1)
    avg_reranked_recall_5 = sum(reranked_recall_5) / max(len(reranked_recall_5), 1)
    avg_reranked_recall_8 = sum(reranked_recall_8) / max(len(reranked_recall_8), 1)
    avg_reranked_recall_10 = sum(reranked_recall_10) / max(len(reranked_recall_10), 1)
    avg_context_hit_5 = sum(context_hit_5) / max(len(context_hit_5), 1)
    avg_context_hit_8 = sum(context_hit_8) / max(len(context_hit_8), 1)
    avg_precision_3 = sum(precision_3) / max(len(precision_3), 1)
    avg_precision_5 = sum(precision_5) / max(len(precision_5), 1)
    avg_precision_8 = sum(precision_8) / max(len(precision_8), 1)
    avg_final_context_recall = sum(final_context_recall) / max(len(final_context_recall), 1)
    avg_final_context_precision = sum(final_context_precision) / max(len(final_context_precision), 1)
    avg_final_context_hit = sum(final_context_hit) / max(len(final_context_hit), 1)
    avg_mrr = sum(mrr_scores) / max(len(mrr_scores), 1)
    avg_ceiling_3 = sum(ceiling_3) / max(len(ceiling_3), 1)
    avg_ceiling_10 = sum(ceiling_10) / max(len(ceiling_10), 1)
    avg_ceiling_20 = sum(ceiling_20) / max(len(ceiling_20), 1)
    avg_normalized_candidate_recall_10 = sum(normalized_candidate_recall_10) / max(len(normalized_candidate_recall_10), 1)
    avg_normalized_candidate_recall_20 = sum(normalized_candidate_recall_20) / max(len(normalized_candidate_recall_20), 1)
    avg_normalized_reranked_recall_3 = sum(normalized_reranked_recall_3) / max(len(normalized_reranked_recall_3), 1)
    avg_normalized_reranked_recall_5 = sum(normalized_reranked_recall_5) / max(len(normalized_reranked_recall_5), 1)
    avg_normalized_reranked_recall_8 = sum(normalized_reranked_recall_8) / max(len(normalized_reranked_recall_8), 1)
    avg_normalized_context_hit_5 = sum(normalized_context_hit_5) / max(len(normalized_context_hit_5), 1)
    avg_normalized_context_hit_8 = sum(normalized_context_hit_8) / max(len(normalized_context_hit_8), 1)

    # Per-route metrics
    by_route: dict[str, dict[str, Any]] = {}
    for row, cr10, cr20, rr3, rr5, rr8, ch5, ch8, p3, p5, p8, mr, c3, c10, c20, ncr10, ncr20, nrr3, nrr5, nrr8, nch5, nch8 in zip(
        rows, candidate_recall_10, candidate_recall_20, reranked_recall_3, reranked_recall_5, reranked_recall_8,
        context_hit_5, context_hit_8, precision_3, precision_5, precision_8, mrr_scores, ceiling_3, ceiling_10, ceiling_20,
        normalized_candidate_recall_10, normalized_candidate_recall_20,
        normalized_reranked_recall_3, normalized_reranked_recall_5, normalized_reranked_recall_8,
        normalized_context_hit_5, normalized_context_hit_8,
    ):
        rt = row["route"]
        if rt not in by_route:
            by_route[rt] = {
                "cr10_sum": 0, "cr20_sum": 0, "rr3_sum": 0, "rr5_sum": 0, "rr8_sum": 0,
                "ch5_sum": 0, "ch8_sum": 0,
                "p3_sum": 0, "p5_sum": 0, "p8_sum": 0,
                "mr_sum": 0, "c3_sum": 0, "c10_sum": 0, "c20_sum": 0,
                "ncr10_sum": 0, "ncr20_sum": 0, "nrr3_sum": 0, "nrr5_sum": 0, "nrr8_sum": 0,
                "nch5_sum": 0, "nch8_sum": 0,
                "count": 0,
            }
        by_route[rt]["cr10_sum"] += cr10
        by_route[rt]["cr20_sum"] += cr20
        by_route[rt]["rr3_sum"] += rr3
        by_route[rt]["rr5_sum"] += rr5
        by_route[rt]["rr8_sum"] += rr8
        by_route[rt]["ch5_sum"] += ch5
        by_route[rt]["ch8_sum"] += ch8
        by_route[rt]["p3_sum"] += p3
        by_route[rt]["p5_sum"] += p5
        by_route[rt]["p8_sum"] += p8
        by_route[rt]["mr_sum"] += mr
        by_route[rt]["c3_sum"] += c3
        by_route[rt]["c10_sum"] += c10
        by_route[rt]["c20_sum"] += c20
        by_route[rt]["ncr10_sum"] += ncr10
        by_route[rt]["ncr20_sum"] += ncr20
        by_route[rt]["nrr3_sum"] += nrr3
        by_route[rt]["nrr5_sum"] += nrr5
        by_route[rt]["nrr8_sum"] += nrr8
        by_route[rt]["nch5_sum"] += nch5
        by_route[rt]["nch8_sum"] += nch8
        by_route[rt]["count"] += 1

    route_metrics = {}
    for rt, d in by_route.items():
        n = max(d["count"], 1)
        route_metrics[rt] = {
            "candidate_recall@10": round(d["cr10_sum"] / n, 4),
            "candidate_recall@20": round(d["cr20_sum"] / n, 4),
            "reranked_recall@3": round(d["rr3_sum"] / n, 4),
            "reranked_recall@5": round(d["rr5_sum"] / n, 4),
            "reranked_recall@8": round(d["rr8_sum"] / n, 4),
            "context_hit@5": round(d["ch5_sum"] / n, 4),
            "context_hit@8": round(d["ch8_sum"] / n, 4),
            "precision@3": round(d["p3_sum"] / n, 4),
            "precision@5": round(d["p5_sum"] / n, 4),
            "precision@8": round(d["p8_sum"] / n, 4),
            "mrr": round(d["mr_sum"] / n, 4),
            "ceiling@3": round(d["c3_sum"] / n, 4),
            "ceiling@10": round(d["c10_sum"] / n, 4),
            "ceiling@20": round(d["c20_sum"] / n, 4),
            "normalized_candidate_recall@10": round(d["ncr10_sum"] / n, 4),
            "normalized_candidate_recall@20": round(d["ncr20_sum"] / n, 4),
            "normalized_reranked_recall@3": round(d["nrr3_sum"] / n, 4),
            "normalized_reranked_recall@5": round(d["nrr5_sum"] / n, 4),
            "normalized_reranked_recall@8": round(d["nrr8_sum"] / n, 4),
            "normalized_context_hit@5": round(d["nch5_sum"] / n, 4),
            "normalized_context_hit@8": round(d["nch8_sum"] / n, 4),
            "count": d["count"],
        }

    # Error analysis
    error_analysis = {}
    if verbose and errors:
        candidate_miss = sum(1 for e in errors if e.get("miss_type") == "candidate_miss")
        rerank_miss = sum(1 for e in errors if e.get("miss_type") == "rerank_miss")
        recall_10_miss = sum(1 for e in errors if e.get("miss_type") == "recall_10_candidate_miss")
        retrieval_error = sum(1 for e in errors if e.get("miss_type") == "retrieval_error")
        error_analysis = {
            "total_errors": len(errors),
            "candidate_miss": candidate_miss,  # Gold not in top20
            "recall_10_candidate_miss": recall_10_miss,  # Gold in top20 but not top10
            "rerank_miss": rerank_miss,  # Gold in candidate pool but not in final top3
            "retrieval_error": retrieval_error,
            "candidate_miss_rate": round(candidate_miss / len(errors), 4) if errors else 0,
            "rerank_miss_rate": round(rerank_miss / len(errors), 4) if errors else 0,
        }

        # Analyze by gold count groups
        by_gold_count = {"small": [], "medium": [], "large": []}
        for err in errors:
            gc = int(err.get("gold_count", 0))
            if gc <= 3:
                by_gold_count["small"].append(err)
            elif gc <= 10:
                by_gold_count["medium"].append(err)
            else:
                by_gold_count["large"].append(err)

        error_analysis["by_gold_count"] = {
            "small (<=3)": {
                "count": len(by_gold_count["small"]),
                "avg_recall@3": round(sum(e.get("recall@3", 0.0) for e in by_gold_count["small"]) / max(len(by_gold_count["small"]), 1), 4),
                "avg_recall@10": round(sum(e.get("recall@10", 0.0) for e in by_gold_count["small"]) / max(len(by_gold_count["small"]), 1), 4),
                "avg_ceiling@3": round(sum(e.get("ceiling@3", 0.0) for e in by_gold_count["small"]) / max(len(by_gold_count["small"]), 1), 4),
            },
            "medium (4-10)": {
                "count": len(by_gold_count["medium"]),
                "avg_recall@3": round(sum(e.get("recall@3", 0.0) for e in by_gold_count["medium"]) / max(len(by_gold_count["medium"]), 1), 4),
                "avg_recall@10": round(sum(e.get("recall@10", 0.0) for e in by_gold_count["medium"]) / max(len(by_gold_count["medium"]), 1), 4),
                "avg_ceiling@3": round(sum(e.get("ceiling@3", 0.0) for e in by_gold_count["medium"]) / max(len(by_gold_count["medium"]), 1), 4),
            },
            "large (>10)": {
                "count": len(by_gold_count["large"]),
                "avg_recall@3": round(sum(e.get("recall@3", 0.0) for e in by_gold_count["large"]) / max(len(by_gold_count["large"]), 1), 4),
                "avg_recall@10": round(sum(e.get("recall@10", 0.0) for e in by_gold_count["large"]) / max(len(by_gold_count["large"]), 1), 4),
                "avg_ceiling@3": round(sum(e.get("ceiling@3", 0.0) for e in by_gold_count["large"]) / max(len(by_gold_count["large"]), 1), 4),
            },
        }

    details: dict[str, Any] = {
        "params": {
            "candidate_k": candidate_k,
            "final_k": final_k,
            "fusion_weights": fusion_weights,
            "max_query_results": MAX_QUERY_RESULTS,
        },
        "candidate_recall@10": round(avg_candidate_recall_10, 4),
        "candidate_recall@20": round(avg_candidate_recall_20, 4),
        "reranked_recall@3": round(avg_reranked_recall_3, 4),
        "reranked_recall@5": round(avg_reranked_recall_5, 4),
        "reranked_recall@8": round(avg_reranked_recall_8, 4),
        "reranked_recall@10": round(avg_reranked_recall_10, 4),
        "context_hit@5": round(avg_context_hit_5, 4),
        "context_hit@8": round(avg_context_hit_8, 4),
        "precision@3": round(avg_precision_3, 4),
        "precision@5": round(avg_precision_5, 4),
        "precision@8": round(avg_precision_8, 4),
        f"final_context_recall@{final_k}": round(avg_final_context_recall, 4),
        f"final_context_precision@{final_k}": round(avg_final_context_precision, 4),
        f"final_context_hit@{final_k}": round(avg_final_context_hit, 4),
        "mrr": round(avg_mrr, 4),
        "ceiling@3": round(avg_ceiling_3, 4),
        "ceiling@10": round(avg_ceiling_10, 4),
        "ceiling@20": round(avg_ceiling_20, 4),
        "normalized_candidate_recall@10": round(avg_normalized_candidate_recall_10, 4),
        "normalized_candidate_recall@20": round(avg_normalized_candidate_recall_20, 4),
        "normalized_reranked_recall@3": round(avg_normalized_reranked_recall_3, 4),
        "normalized_reranked_recall@5": round(avg_normalized_reranked_recall_5, 4),
        "normalized_reranked_recall@8": round(avg_normalized_reranked_recall_8, 4),
        "normalized_context_hit@5": round(avg_normalized_context_hit_5, 4),
        "normalized_context_hit@8": round(avg_normalized_context_hit_8, 4),
        "by_route": route_metrics,
    }
    if verbose:
        details["errors"] = errors[:50]
        details["error_analysis"] = error_analysis

    return StageResult(
        stage="chunk_retrieval",
        primary_metric="reranked_recall@3",
        value=round(avg_reranked_recall_3, 4),
        gold_size=len(rows),
        details=details,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate chunk retrieval stage with two-stage metrics.")
    parser.add_argument("--candidate-k", type=int, default=20, help="Candidate pool size")
    parser.add_argument("--final-k", type=int, default=3, help="Final top-k returned to LLM")
    parser.add_argument("--route", choices=["tutor", "customer"], help="Filter by route")
    parser.add_argument("--verbose", action="store_true", help="Include detailed error analysis")
    parser.add_argument("--save-verbose", action="store_true", help="Save verbose errors to file")
    args = parser.parse_args()

    result = evaluate(
        candidate_k=args.candidate_k,
        final_k=args.final_k,
        route_filter=args.route,
        verbose=args.verbose,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if args.save_verbose and args.verbose and "errors" in result.details:
        verbose_path = f"data/eval/retrieval_verbose_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(verbose_path, "w", encoding="utf-8") as f:
            json.dump({"stage": "chunk_retrieval", "details": result.details}, f, ensure_ascii=False, indent=2)
        print(f"\nVerbose errors saved to {verbose_path}")


if __name__ == "__main__":
    main()
