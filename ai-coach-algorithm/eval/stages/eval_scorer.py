"""Scorer-quality evaluation on FIXED transcripts.

Why this stage exists (2026-07-09 finding): the e2e stage feeds *fixed*
employee scripts into a *dynamic* LLM customer, so the resulting dialogs are
inherently incoherent — the LLM judge then (correctly) penalizes "答非所问",
and its scores can't be compared against gold bands that were calibrated on
the rule scorer. Conclusions about scorer quality were impossible to draw.

This stage removes both confounds: every case is a complete, frozen
transcript (customer questions AND employee answers fixed). The finish
scoring path runs exactly as production does (tutor retrieval → coverage →
LLM-first scoring with red-line cross-check → rule fallback), and the score
is checked against a band that a human assigned to THIS transcript.

Gold file: data/eval/scorer_transcript_gold.jsonl, one JSON per line:
    {
      "id": "scorer_001",
      "scene_id": "INS_PERIODIC",
      "dialog_pairs": [{"customer_question": "...", "employee_answer": "..."}],
      "expected_score_range": [60, 75],
      "expected_weak_tags": [],
      "quality": "good|partial|poor",
      "band_status": "reviewed|draft",   # draft = band copied from old gold, pending human review
      "transcript_hash": "sha256 bound to scene_id + complete dialog_pairs",
      "note": ""
    }

The primary metric is computed over *reviewed* cases when any exist; draft
cases are reported separately so machine-copied bands never masquerade as a
human-calibrated result.

Bootstrap gold candidates from a real e2e run with:
    python scripts/build_scorer_gold_from_e2e_verbose.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from typing import Any

from eval.metrics import StageResult
from app.core.weakness_taxonomy import normalize_weakness_tags, weakness_tag_matches
from eval.scorer_fingerprint import (
    compute_scorer_config_fingerprint,
    load_blessed_fingerprint,
)
from eval.transcript import transcript_hash

GOLD_PATH = Path("data/eval/scorer_transcript_gold.jsonl")


def _load_gold(gold_path: Path) -> list[dict[str, Any]]:
    if not gold_path.exists():
        raise FileNotFoundError(f"scorer gold not found: {gold_path}")
    cases = []
    with open(gold_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _tags_overlap(expected: str, detected: str) -> bool:
    """Match through the production taxonomy, not arbitrary 2-char overlap."""
    return weakness_tag_matches(expected, detected)


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run the production finish-scoring path on one frozen transcript."""
    # Local imports keep `python -m eval.run_all --stages retrieval` etc. from
    # paying the dialog_manager import cost.
    from app.core.dialog_manager import _score_finish
    from app.core.marketing_rag import retrieve_marketing_knowledge
    from app.core.scoring_criteria_loader import get_primary_criterion

    scene_id = case.get("scene_id")
    dialog_pairs = case.get("dialog_pairs") or []
    actual_transcript_hash = transcript_hash(case.get("scene_id"), dialog_pairs)
    expected_transcript_hash = case.get("transcript_hash")
    transcript_integrity_pass = bool(
        expected_transcript_hash and expected_transcript_hash == actual_transcript_hash
    )
    employee_answers = [p.get("employee_answer", "") for p in dialog_pairs if p.get("employee_answer")]
    final_answer = "\n\n".join(employee_answers)

    criterion = get_primary_criterion(scene_id)
    retrieval = retrieve_marketing_knowledge(
        final_answer,
        route="tutor",
        final_k=8,
        scene_id=scene_id,
        must_points=criterion.get("must_points") or None,
        answer_goal=criterion.get("answer_goal"),
        key_terms=criterion.get("key_terms") or None,
    )
    coverage = retrieval.get("retrieval_trace", {}).get("must_point_coverage") or {}

    score = asyncio.run(_score_finish(
        final_answer,
        retrieval.get("items", []),
        criterion=criterion,
        coverage=coverage,
        dialog_pairs=dialog_pairs,
    ))

    total = int(score.get("total_score", 0))
    band = case.get("expected_score_range", [0, 100])
    detected_tags = score.get("weakness_tags", [])
    expected_tags = case.get("expected_weak_tags", [])
    # Both production output and evaluation use the same explicit taxonomy.
    # Known aliases map to canonical IDs; unrelated labels never pass because
    # they happen to share a two-character fragment.
    tag_pass = all(
        any(_tags_overlap(exp, det) for det in detected_tags) for exp in expected_tags
    ) if expected_tags else True
    expected_tag_set = set(normalize_weakness_tags(expected_tags))
    detected_tag_set = set(normalize_weakness_tags(detected_tags))
    tag_tp = len(expected_tag_set & detected_tag_set)
    tag_fp = len(detected_tag_set - expected_tag_set)
    tag_fn = len(expected_tag_set - detected_tag_set)

    return {
        "id": case.get("id"),
        "scene_id": scene_id,
        "quality": case.get("quality", ""),
        "band_status": case.get("band_status", "draft"),
        "expected_range": band,
        "actual_score": total,
        "band_pass": transcript_integrity_pass and band[0] <= total <= band[1],
        "band_distance": 0 if band[0] <= total <= band[1] else min(abs(total - band[0]), abs(total - band[1])),
        "tag_pass": tag_pass,
        "tag_exact_match_pass": expected_tag_set == detected_tag_set,
        "tag_tp": tag_tp,
        "tag_fp": tag_fp,
        "tag_fn": tag_fn,
        "transcript_integrity_pass": transcript_integrity_pass,
        "detected_tags": detected_tags,
        "expected_tags": expected_tags,
        "scorer_method": score.get("method", "unknown"),
    }


def evaluate(
    gold_path: Path | None = None,
    verbose: bool = False,
    require_llm: bool = True,
    case_ids: set[str] | None = None,
) -> StageResult:
    if require_llm:
        from app.core.llm.client import is_llm_available

        if not is_llm_available():
            raise RuntimeError("scorer baseline requires DEEPSEEK_API_KEY; rule fallback is not citable")
        if importlib.util.find_spec("openai") is None:
            raise RuntimeError("scorer baseline requires the openai SDK; rule fallback is not citable")

    all_cases = _load_gold(gold_path or GOLD_PATH)
    cases = [case for case in all_cases if case.get("id") in case_ids] if case_ids else all_cases
    if not cases:
        raise ValueError(f"no scorer cases matched case_ids={sorted(case_ids or [])}")
    invalid_transcripts = [
        str(case.get("id", "unknown"))
        for case in cases
        if case.get("transcript_hash")
        != transcript_hash(case.get("scene_id"), case.get("dialog_pairs") or [])
    ]
    if invalid_transcripts:
        raise RuntimeError(
            "reviewed scorer bands are not valid for the current transcript text: "
            + ", ".join(invalid_transcripts[:10])
        )
    results = [_score_case(case) for case in cases]

    reviewed = [r for r in results if r["band_status"] == "reviewed"]
    drafts = [r for r in results if r["band_status"] != "reviewed"]
    primary_pool = reviewed if reviewed else results
    primary_basis = "reviewed" if reviewed else "all_cases_draft"

    def rate(pool: list[dict[str, Any]], key: str) -> float:
        return round(sum(1 for r in pool if r[key]) / len(pool), 4) if pool else 0.0

    method_dist: dict[str, int] = {}
    for r in results:
        method_dist[r["scorer_method"]] = method_dist.get(r["scorer_method"], 0) + 1

    non_llm = [r for r in results if not str(r.get("scorer_method", "")).startswith("llm_scorer")]
    if require_llm and non_llm:
        fallback_methods = sorted({str(r.get("scorer_method", "unknown")) for r in non_llm})
        raise RuntimeError(
            "scorer baseline requires LLM-only execution, but "
            f"{len(non_llm)}/{len(results)} cases used fallback methods: {fallback_methods}. "
            "Install/configure the OpenAI-compatible SDK and DEEPSEEK_API_KEY, "
            "or pass --allow-rule-fallback for diagnostics only."
        )

    failures = [
        {k: r[k] for k in (
            "id", "quality", "band_status", "expected_range", "actual_score",
            "band_distance", "scorer_method", "transcript_integrity_pass",
        )}
        for r in results if not r["band_pass"]
    ]
    failures.sort(key=lambda f: -f["band_distance"])
    tag_failures = [
        {
            "id": r["id"],
            "quality": r["quality"],
            "expected_tags": r["expected_tags"],
            "detected_tags": r["detected_tags"],
            "scorer_method": r["scorer_method"],
        }
        for r in results if not r["tag_pass"]
    ]
    tag_tp = sum(r["tag_tp"] for r in results)
    tag_fp = sum(r["tag_fp"] for r in results)
    tag_fn = sum(r["tag_fn"] for r in results)
    tag_precision = tag_tp / (tag_tp + tag_fp) if tag_tp + tag_fp else 1.0
    tag_recall = tag_tp / (tag_tp + tag_fn) if tag_tp + tag_fn else 1.0
    tag_f1 = (
        2 * tag_precision * tag_recall / (tag_precision + tag_recall)
        if tag_precision + tag_recall else 0.0
    )

    if verbose:
        for f in failures:
            print(f"  MISS {f['id']} [{f['quality']}/{f['band_status']}] "
                  f"expected {f['expected_range']} got {f['actual_score']} ({f['scorer_method']})")
        for f in tag_failures:
            print(
                f"  TAG MISS {f['id']} expected {f['expected_tags']} "
                f"got {f['detected_tags']} ({f['scorer_method']})"
            )

    # Config fingerprint: the frozen 0.94 baseline is only citable while the
    # scorer that produced it is byte-identical. A mismatch does not fail the
    # run (diagnostics stay useful) but it strips citability until the new
    # config is re-baselined and blessed.
    current_fp = compute_scorer_config_fingerprint()
    blessed = load_blessed_fingerprint()
    fingerprint_match = bool(blessed and blessed.get("fingerprint") == current_fp["fingerprint"])
    if blessed and not fingerprint_match:
        print(
            "WARNING: scorer config changed since the blessed baseline "
            f"(blessed {blessed.get('blessed_at', '?')}). Results are diagnostic only; "
            "rerun the full 50-case suite and re-bless with --bless-fingerprint."
        )

    return StageResult(
        stage="scorer_transcript",
        primary_metric="score_band_pass",
        value=rate(primary_pool, "band_pass"),
        gold_size=len(primary_pool),
        details={
            "primary_basis": primary_basis,
            "citable_full_baseline": len(cases) == len(all_cases) and (blessed is None or fingerprint_match),
            "scorer_config_fingerprint": current_fp["fingerprint"],
            "baseline_fingerprint_match": fingerprint_match if blessed else None,
            "selected_case_ids": sorted(case_ids) if case_ids else [],
            "total_gold_cases": len(all_cases),
            "total_cases": len(results),
            "reviewed_cases": len(reviewed),
            "draft_cases": len(drafts),
            "band_pass_all": rate(results, "band_pass"),
            "band_pass_reviewed": rate(reviewed, "band_pass"),
            "band_pass_draft": rate(drafts, "band_pass"),
            "tag_pass": rate(results, "tag_pass"),
            "tag_exact_match_pass": rate(results, "tag_exact_match_pass"),
            "tag_micro_precision": round(tag_precision, 4),
            "tag_micro_recall": round(tag_recall, 4),
            "tag_micro_f1": round(tag_f1, 4),
            "tag_annotation_contract": "provisional_required_tags_not_exhaustive",
            "transcript_integrity_pass": rate(results, "transcript_integrity_pass"),
            "mean_band_distance": round(
                sum(r["band_distance"] for r in results) / len(results), 2
            ) if results else 0.0,
            "scorer_method_distribution": method_dist,
            "failures": failures[:20],
            "tag_failures": tag_failures[:20],
            **({
                "tag_case_results": [
                    {
                        "id": r["id"],
                        "expected_tags": r["expected_tags"],
                        "detected_tags": r["detected_tags"],
                        "tag_exact_match_pass": r["tag_exact_match_pass"],
                    }
                    for r in results
                ]
            } if verbose else {}),
        },
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate finish scoring on fixed transcripts.")
    parser.add_argument("--gold-path", type=Path, default=GOLD_PATH)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Run only the named case; repeat for multiple cases. Subset results are not citable baselines.",
    )
    parser.add_argument(
        "--allow-rule-fallback",
        action="store_true",
        help="Diagnostic only: allow rule-scored cases instead of failing the formal LLM baseline.",
    )
    parser.add_argument(
        "--bless-fingerprint",
        action="store_true",
        help="After a full-gold LLM-only run, record the current scorer config as the frozen-baseline config.",
    )
    args = parser.parse_args()
    result = evaluate(
        gold_path=args.gold_path,
        verbose=args.verbose,
        require_llm=not args.allow_rule_fallback,
        case_ids=set(args.case_id) or None,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))

    if args.bless_fingerprint:
        from eval.scorer_fingerprint import bless_fingerprint

        details = result.details
        if args.case_id or args.allow_rule_fallback:
            raise SystemExit("refusing to bless: fingerprint may only be blessed on a full-gold, LLM-only run")
        bless_fingerprint(
            compute_scorer_config_fingerprint(),
            baseline_summary={
                "score_band_pass": result.value,
                "mean_band_distance": details.get("mean_band_distance"),
                "gold_size": result.gold_size,
                "run_primary_basis": details.get("primary_basis"),
            },
        )
        print("Blessed current scorer config as the frozen-baseline fingerprint.")


if __name__ == "__main__":
    main()
