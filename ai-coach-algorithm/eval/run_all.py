"""Run all RAG evaluation stages and produce a unified report.

Usage:
    python -m eval.run_all --stages all
    python -m eval.run_all --stages intent,retrieval
    python -m eval.run_all --stages intent --verbose
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eval.metrics import StageResult
from eval.report import build_report, format_ascii_table, save_report

DEFAULT_STAGES = ["llm_intent", "gap", "retrieval", "must_point", "e2e"]
AVAILABLE_STAGES = ["intent", "llm_intent", "gap", "retrieval", "must_point", "e2e"]


def _run_intent(verbose: bool = False) -> StageResult:
    from eval.stages.eval_intent import evaluate
    return evaluate(verbose=verbose)


def _run_llm_intent(verbose: bool = False) -> StageResult:
    from eval.stages.eval_llm_intent import evaluate_stage
    return evaluate_stage(sample_size=50, verbose=verbose, cached_ok=True)


def _run_gap(verbose: bool = False) -> StageResult:
    from eval.stages.eval_gap import evaluate
    gold_path = Path("data/eval/gap_computation_gold.jsonl")
    if not gold_path.exists():
        print("Gap gold not found. Generating...")
        from eval.gold_builder.build_gap_gold import save
        save()
    return evaluate(verbose=verbose)


def _run_retrieval(verbose: bool = False) -> StageResult:
    from eval.stages.eval_retrieval import evaluate
    gold_path = Path("data/eval/retrieval_gold.jsonl")
    if not gold_path.exists():
        print("Retrieval gold not found. Generating...")
        from eval.gold_builder.build_retrieval_gold import save
        save()
    # Match the production finish path: recall a wider pool, rerank locally,
    # and pass a compact context pack to the scorer LLM.
    return evaluate(candidate_k=40, final_k=8, verbose=verbose)


def _run_must_point(verbose: bool = False) -> StageResult:
    from eval.stages.eval_must_point import evaluate
    gold_path = Path("data/eval/must_point_coverage_gold.jsonl")
    if not gold_path.exists():
        print("Must-point gold not found. Generating...")
        from eval.gold_builder.build_must_point_gold import save
        save()
    return evaluate(verbose=verbose)


def _run_e2e(verbose: bool = False) -> StageResult:
    from eval.stages.eval_e2e import evaluate
    # Use all available gold cases (no sample_size limit) for comprehensive evaluation
    return evaluate(sample_size=None, verbose=verbose, skip_slow=False)


RUNNERS = {
    "intent": _run_intent,
    "llm_intent": _run_llm_intent,
    "gap": _run_gap,
    "retrieval": _run_retrieval,
    "must_point": _run_must_point,
    "e2e": _run_e2e,
}


def run(stages: list[str], verbose: bool = False) -> list[StageResult]:
    results = []
    for stage in stages:
        if stage not in RUNNERS:
            print(f"Unknown stage: {stage}, skipping")
            continue
        print(f"\n--- Running {stage} evaluation ---")
        try:
            result = RUNNERS[stage](verbose=verbose)
            results.append(result)
            print(f"  {stage}: {result.primary_metric} = {result.value:.4f} (n={result.gold_size})")
        except FileNotFoundError as e:
            print(f"  {stage}: SKIPPED — {e}")
        except Exception as e:
            print(f"  {stage}: ERROR — {e}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG per-stage evaluation.")
    parser.add_argument(
        "--stages",
        default="all",
        help=(
            f"Comma-separated stage names or 'all'. Available: {', '.join(AVAILABLE_STAGES)}. "
            f"'all' uses current production stages: {', '.join(DEFAULT_STAGES)}"
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--output", default="data/eval/report.json")
    args = parser.parse_args()

    if args.stages == "all":
        stages = DEFAULT_STAGES
    else:
        stages = [s.strip() for s in args.stages.split(",")]

    results = run(stages, verbose=args.verbose)
    if results:
        report = build_report(results)
        print("\n" + format_ascii_table(report))
        save_report(report, args.output)


if __name__ == "__main__":
    main()
