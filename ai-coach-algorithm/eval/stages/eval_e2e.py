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
import os
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
        StageResult with dynamic_dialogue_pass as the primary metric. The
        legacy-unbound finish score bands remain visible only as diagnostics.
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

    total_employee_turns = sum(len(case.get("employee_messages") or []) for case in gold_cases)
    reviewed_direction_turns = sum(
        len(case.get("expected_followup_direction") or []) for case in gold_cases
    )
    details: dict[str, Any] = {
        "evaluation_schema_version": 2,
        "metric_contract": "dual_route_evidence_and_canonical_tags_v2",
        "primary_metric_contract": "dynamic_start_reply_quality",
        "dynamic_score_band_contract": "legacy_unbound_diagnostic_only",
        "total_cases": len(results),
        "gold_annotation_coverage": {
            "total_employee_turns": total_employee_turns,
            "reviewed_followup_turns": reviewed_direction_turns,
            "followup_turn_coverage": round(
                reviewed_direction_turns / total_employee_turns, 4
            ) if total_employee_turns else 0.0,
        },
        "sample_size": sample_size,
        "skip_slow": skip_slow,
        "runtime_config": {
            "customer_llm_mode": os.getenv("AI_COACH_CUSTOMER_LLM", "llm"),
            "scorer_mode": os.getenv("AI_COACH_SCORER", "llm"),
            "embedding_backend": os.getenv("AI_COACH_EMBEDDING_BACKEND", "sentence_transformers"),
            "embedding_model": os.getenv("AI_COACH_EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),
            "followup_semantic_threshold": os.getenv(
                "AI_COACH_E2E_FOLLOWUP_SEMANTIC_THRESHOLD",
                "backend_default",
            ),
        },
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

        # Compact transcript of EVERY case (pass or fail) — the raw material
        # for building scorer_transcript gold via
        # scripts/build_scorer_gold_from_e2e_verbose.py.
        details["case_transcripts"] = [
            {
                "case_id": r.get("case_id"),
                "scene_id": r.get("scene_id"),
                "opening": r.get("start_trace", {}).get("opening", ""),
                "customer_messages": [
                    reply.get("ai_customer_message")
                    for reply in r.get("reply_results", [])
                    if reply.get("ai_customer_message")
                ],
                # Per-turn follow-up verdicts — the raw material for the
                # follow-up checker credibility audit
                # (scripts/build_followup_audit.py).
                "turns": [
                    {
                        "round": reply.get("round"),
                        "ai_customer_message": reply.get("ai_customer_message"),
                        "followup_pass": reply.get("followup_pass"),
                        "followup_method": reply.get("followup_method"),
                        "followup_reason": reply.get("followup_reason"),
                        "expected_direction": (reply.get("followup_trace") or {}).get("expected_direction"),
                        "gap_intents": (reply.get("followup_trace") or {}).get("gap_intents"),
                    }
                    for reply in r.get("reply_results", [])
                ],
                "actual_score": r.get("finish_trace", {}).get("total_score"),
                "scorer_method": r.get("scorer_method"),
                "overall_pass": r.get("overall_pass"),
            }
            for r in results
        ]

    return _get_eval_impl()["StageResult"](
        stage="e2e_dialogue",
        primary_metric="dynamic_dialogue_pass",
        value=round(metrics.get("dynamic_dialogue_pass", 0.0), 4),
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
        "tutor_retrieval_hit": 0,
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


# Version-controlled fields that are counts/config, not quality metrics —
# excluded from multi-run aggregation.
_NON_METRIC_NUMERIC_KEYS = {
    "evaluation_schema_version", "total_cases", "sample_size",
    "failure_count", "strict_failure_count",
}


def evaluate_runs(
    runs: int = 1,
    **kwargs: Any,
) -> "StageResult":
    """Run the dynamic E2E evaluation `runs` times and aggregate.

    The LLM customer is stochastic (temperature 0.7), so a single run of any
    dynamic metric is a sample, not an estimate. With runs >= 2 the report
    carries mean/min/max per metric and the primary value becomes the mean.
    A single run is always stamped `single_run_not_citable=true`.
    """
    if runs <= 1:
        result = evaluate(**kwargs)
        result.details["runs"] = 1
        result.details["single_run_not_citable"] = True
        return result

    results = [evaluate(**kwargs) for _ in range(runs)]
    last = results[-1]

    metric_keys = [
        k for k, v in last.details.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
        and k not in _NON_METRIC_NUMERIC_KEYS
    ]
    aggregate: dict[str, Any] = {}
    for key in metric_keys:
        values = [r.details.get(key) for r in results]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in values):
            continue
        aggregate[key] = {
            "mean": round(sum(values) / len(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "runs": [round(v, 4) for v in values],
        }
        # Surface the mean as the headline number for each metric.
        last.details[key] = aggregate[key]["mean"]

    last.details["runs"] = runs
    last.details["single_run_not_citable"] = False
    last.details["aggregate"] = aggregate
    primary = last.primary_metric
    if primary in aggregate:
        last.value = aggregate[primary]["mean"]
    return last


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate end-to-end dialogue quality.")
    parser.add_argument("--gold-path", type=Path, help="Path to gold JSONL file")
    parser.add_argument("--sample-size", type=int, help="Limit evaluation to N cases")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--skip-slow", action="store_true", help="Skip LLM-dependent validation")
    parser.add_argument("--save-trace", action="store_true", help="Save full trace to file")
    parser.add_argument(
        "--runs", type=int, default=1,
        help="Repeat the dynamic evaluation N times and report mean/min/max. "
             "Single runs are stamped single_run_not_citable.",
    )
    args = parser.parse_args()

    result = evaluate_runs(
        runs=args.runs,
        gold_path=args.gold_path,
        sample_size=args.sample_size,
        verbose=args.verbose,
        skip_slow=args.skip_slow,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if args.save_trace and (
        result.details.get("case_transcripts") or result.details.get("failure_samples")
    ):
        trace_path = Path(f"data/eval/e2e_verbose_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        save_trace({"result": result.to_dict()}, trace_path)
        print(f"\nVerbose trace saved to {trace_path}")


if __name__ == "__main__":
    main()
