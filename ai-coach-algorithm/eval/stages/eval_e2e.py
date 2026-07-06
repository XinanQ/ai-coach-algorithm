"""Stage 5: End-to-end dialogue evaluation.

Simulates complete dialogue flows (start -> multi-round reply -> finish) and
validates each stage against gold expectations:
- Contract compliance (no liveScore/source in reply)
- Intent detection per turn
- Gap computation accuracy
- RAG retrieval context quality
- Follow-up direction correctness
- Final score reasonableness
- Weak tag relevance

Each E2E case represents a complete training scenario with employee responses
and expected outcomes at each turn.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Defer heavy imports to avoid blocking module load
_eval_impl = None


def _get_eval_impl():
    """Lazy-load the E2E evaluation implementation to avoid circular imports."""
    global _eval_impl
    if _eval_impl is None:
        import sys
        # Ensure project root is in path (eval_e2e.py is in eval/stages/, need to go up 3 levels)
        root = Path(__file__).parent.parent.parent.resolve()
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        from eval.metrics import StageResult
        from eval.stages._eval_e2e_impl import (
            E2EEvaluator,
            compute_e2e_metrics,
            load_e2e_gold,
            save_e2e_trace,
        )
        _eval_impl = {
            "StageResult": StageResult,
            "E2EEvaluator": E2EEvaluator,
            "compute_e2e_metrics": compute_e2e_metrics,
            "load_e2e_gold": load_e2e_gold,
            "save_e2e_trace": save_e2e_trace,
        }
    return _eval_impl


def load_gold(path: Path | None = None) -> list[dict[str, Any]]:
    """Load E2E gold dataset.

    Args:
        path: Path to gold JSONL file (default: data/eval/e2e_dialog_gold.jsonl)

    Returns:
        List of E2E test cases
    """
    return _get_eval_impl()["load_e2e_gold"](path)


def evaluate(
    *,
    gold_path: Path | None = None,
    sample_size: int | None = None,
    verbose: bool = False,
    skip_slow: bool = False,
) -> "StageResult":
    """Run end-to-end dialogue evaluation.

    Simulates complete dialogues through start -> reply -> finish and validates
    each stage against gold expectations.

    Args:
        gold_path: Path to gold data file
        sample_size: Limit evaluation to N cases (for faster iteration)
        verbose: Include per-case breakdowns and failure traces
        skip_slow: Skip LLM-dependent validation steps for faster feedback

    Returns:
        StageResult with e2e_overall_pass as primary metric
    """
    impl = _get_eval_impl()
    E2EEvaluator = impl["E2EEvaluator"]
    compute_e2e_metrics = impl["compute_e2e_metrics"]

    gold_cases = impl["load_e2e_gold"](gold_path)
    if sample_size:
        gold_cases = gold_cases[:sample_size]

    evaluator = E2EEvaluator(skip_slow=skip_slow, verbose=verbose)
    results = []

    for case in gold_cases:
        result = evaluator.evaluate_case(case)
        results.append(result)

    metrics = compute_e2e_metrics(results)

    details: dict[str, Any] = {
        "total_cases": len(results),
        "sample_size": sample_size,
        "skip_slow": skip_slow,
        **metrics,
    }

    if verbose and results:
        # Include failure breakdown
        failures = [r for r in results if not r.get("overall_pass", False)]
        strict_failures = [r for r in results if not r.get("strict_overall_pass", False)]
        details["failure_count"] = len(failures)
        details["failures_by_stage"] = _analyze_failures_by_stage(failures)
        details["strict_failure_count"] = len(strict_failures)
        details["strict_failures_by_stage"] = _analyze_failures_by_stage(strict_failures)

        # Include first few failure traces
        details["failure_samples"] = [
            {k: v for k, v in f.items() if k not in ("trace", "dialogue_trace")}
            for f in failures[:5]
        ]

    return _get_eval_impl()["StageResult"](
        stage="e2e_dialogue",
        primary_metric="e2e_overall_pass",
        value=round(metrics.get("e2e_overall_pass", 0.0), 4),
        gold_size=len(gold_cases),
        details=details,
    )


def _analyze_failures_by_stage(failures: list[dict[str, Any]]) -> dict[str, int]:
    """Count which stages failed most often."""
    stage_failures = {
        "start_pass": 0,
        "contract_pass": 0,
        "intent_pass": 0,
        "gap_pass": 0,
        "retrieval_hit": 0,
        "followup_pass": 0,
        "finish_score_pass": 0,
        "strict_score_pass": 0,
        "weak_tag_pass": 0,
    }
    for f in failures:
        for stage in stage_failures:
            if not f.get(stage, True):
                stage_failures[stage] += 1
    return stage_failures


def save_trace(trace: dict[str, Any], path: Path | None = None) -> None:
    """Save detailed E2E execution trace for debugging.

    Args:
        trace: Execution trace from evaluate()
        path: Output file path (default: data/eval/e2e_verbose_TIMESTAMP.json)
    """
    _get_eval_impl()["save_e2e_trace"](trace, path)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate end-to-end dialogue quality.")
    parser.add_argument("--gold-path", type=Path, help="Path to gold JSONL file")
    parser.add_argument("--sample-size", type=int, help="Limit evaluation to N cases")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--skip-slow", action="store_true", help="Skip LLM-dependent validation")
    parser.add_argument("--save-trace", action="store_true", help="Save full trace to file")
    args = parser.parse_args()

    result = evaluate(
        gold_path=args.gold_path,
        sample_size=args.sample_size,
        verbose=args.verbose,
        skip_slow=args.skip_slow,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if args.save_trace and result.details.get("failure_samples"):
        trace_path = Path(f"data/eval/e2e_verbose_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        save_trace({"result": result.to_dict()}, trace_path)
        print(f"\nVerbose trace saved to {trace_path}")


if __name__ == "__main__":
    main()
