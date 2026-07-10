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
import json
from pathlib import Path
from typing import Any

from eval.metrics import StageResult

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
    """True when the two tags share any 2-char fragment (词根级匹配)."""
    if expected in detected or detected in expected:
        return True
    return any(expected[i:i + 2] in detected for i in range(len(expected) - 1))


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    """Run the production finish-scoring path on one frozen transcript."""
    # Local imports keep `python -m eval.run_all --stages retrieval` etc. from
    # paying the dialog_manager import cost.
    from app.core.dialog_manager import _score_finish
    from app.core.marketing_rag import retrieve_marketing_knowledge
    from app.core.scoring_criteria_loader import get_primary_criterion

    scene_id = case.get("scene_id")
    dialog_pairs = case.get("dialog_pairs") or []
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
    # Tag check mirrors the e2e stage's lenient contract: an expected tag is
    # matched when it shares a 2+ char fragment with some detected tag, so
    # synonymous phrasings ("合规问题" vs "合规红线", "不当承诺" vs "绝对化承诺")
    # count as hits — the vocabulary isn't canonicalized yet.
    tag_pass = all(
        any(_tags_overlap(exp, det) for det in detected_tags) for exp in expected_tags
    ) if expected_tags else True

    return {
        "id": case.get("id"),
        "scene_id": scene_id,
        "quality": case.get("quality", ""),
        "band_status": case.get("band_status", "draft"),
        "expected_range": band,
        "actual_score": total,
        "band_pass": band[0] <= total <= band[1],
        "band_distance": 0 if band[0] <= total <= band[1] else min(abs(total - band[0]), abs(total - band[1])),
        "tag_pass": tag_pass,
        "detected_tags": detected_tags,
        "expected_tags": expected_tags,
        "scorer_method": score.get("method", "unknown"),
    }


def evaluate(gold_path: Path | None = None, verbose: bool = False) -> StageResult:
    cases = _load_gold(gold_path or GOLD_PATH)
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

    failures = [
        {k: r[k] for k in ("id", "quality", "band_status", "expected_range", "actual_score", "band_distance", "scorer_method")}
        for r in results if not r["band_pass"]
    ]
    failures.sort(key=lambda f: -f["band_distance"])

    if verbose:
        for f in failures:
            print(f"  MISS {f['id']} [{f['quality']}/{f['band_status']}] "
                  f"expected {f['expected_range']} got {f['actual_score']} ({f['scorer_method']})")

    return StageResult(
        stage="scorer_transcript",
        primary_metric="score_band_pass",
        value=rate(primary_pool, "band_pass"),
        gold_size=len(primary_pool),
        details={
            "primary_basis": primary_basis,
            "total_cases": len(results),
            "reviewed_cases": len(reviewed),
            "draft_cases": len(drafts),
            "band_pass_all": rate(results, "band_pass"),
            "band_pass_reviewed": rate(reviewed, "band_pass"),
            "band_pass_draft": rate(drafts, "band_pass"),
            "tag_pass": rate(results, "tag_pass"),
            "mean_band_distance": round(
                sum(r["band_distance"] for r in results) / len(results), 2
            ) if results else 0.0,
            "scorer_method_distribution": method_dist,
            "failures": failures[:20],
        },
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate finish scoring on fixed transcripts.")
    parser.add_argument("--gold-path", type=Path, default=GOLD_PATH)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    result = evaluate(gold_path=args.gold_path, verbose=args.verbose)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
