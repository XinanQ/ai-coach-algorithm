"""Build the weak-tag audit sheet from a saved scorer report.

Same audit-before-fix workflow as followup (§5) and customer_retrieval (§5b):
extract every per-case tag disagreement between the scorer's detected tags and
the gold expected_weak_tags, one row per (case, tag, kind), so each row can be
judged against the frozen transcript.

kind taxonomy:
  fp — detected but not expected. Verdict to fill:
       justified — the transcript really shows this weakness; gold is
                   non-exhaustive (annotation gap) -> add to gold
       spurious  — the detector over-reports; keep failing (detector backlog)
  fn — expected but not detected. Verdict to fill:
       gold_wrong    — the expected tag doesn't hold on re-read -> remove
       detector_miss — real weakness the detector failed to report; keep
                       failing (detector backlog)

Prerequisite (temp-0 scorer, single run is representative):
    python -m eval.stages.eval_scorer --save-report data/eval/scorer_report_tags.json

Then:
    python scripts/build_tag_audit.py

Human verdicts are preserved only when the case/tag/kind, transcript hash,
expected/detected sets, and source tag-gold fingerprint are unchanged.
Subset, fallback, stale, and incomplete scorer reports are rejected.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.weakness_taxonomy import normalize_weakness_tags
from eval.audit_provenance import (
    audit_context_fingerprint,
    file_fingerprint,
    scorer_gold_fingerprints,
    tag_seed_fingerprint,
    validate_tag_audit_source,
)

REPORT = Path("data/eval/scorer_report_tags.json")
GOLD = Path("data/eval/scorer_transcript_gold.jsonl")
OUT = Path("data/eval/tag_audit.jsonl")
SEED_GOLD = Path("data/eval/scorer_tag_review_seed.jsonl")

TRANSCRIPT_CHARS = 600  # enough context to judge one tag


def _load_gold_by_id() -> dict[str, dict]:
    rows = {}
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def _load_seed_tags() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in SEED_GOLD.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["id"]] = normalize_weakness_tags(row.get("expected_weak_tags"))
    return rows


def _transcript_excerpt(case: dict) -> str:
    parts = []
    for pair in case.get("dialog_pairs") or []:
        parts.append(f"客户:{pair.get('customer_question', '')}")
        parts.append(f"员工:{pair.get('employee_answer', '')}")
    text = " | ".join(parts)
    return text[:TRANSCRIPT_CHARS]


def main() -> None:
    if not REPORT.exists():
        raise SystemExit(
            f"{REPORT} not found. Run first:\n"
            "  python -m eval.stages.eval_scorer --save-report data/eval/scorer_report_tags.json"
        )
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    tag_cases = (report.get("details") or {}).get("tag_case_results") or []
    if not tag_cases:
        raise SystemExit("report has no tag_case_results — was it saved via --save-report / --verbose?")

    gold_by_id = _load_gold_by_id()
    gold_cases = list(gold_by_id.values())
    validation_errors = validate_tag_audit_source(report, gold_cases)
    if validation_errors:
        raise SystemExit(
            "refusing to build tag audit from an untrusted report:\n- "
            + "\n- ".join(validation_errors)
        )
    source_report_fingerprint = file_fingerprint(REPORT)
    gold_fps = scorer_gold_fingerprints(gold_cases)
    seed_tags_by_id = _load_seed_tags()
    if set(seed_tags_by_id) != set(gold_by_id):
        raise SystemExit("tag review seed case set does not match scorer gold")
    seed_fingerprint = tag_seed_fingerprint(seed_tags_by_id)

    # Preserve human verdicts only when every piece of judging context matches.
    prior: dict[tuple[str, str, str], dict] = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                prior[(row["case_id"], row["tag"], row["kind"])] = row

    rows = []
    n_fp = n_fn = 0
    for tc in tag_cases:
        case_id = tc["id"]
        gold = gold_by_id.get(case_id, {})
        pending = set(normalize_weakness_tags(tc.get("expected_tags")))
        seed = set(seed_tags_by_id[case_id])
        detected = set(normalize_weakness_tags(tc.get("detected_tags")))
        diff_origins: dict[tuple[str, str], set[str]] = {}
        for tag in pending - seed:
            diff_origins.setdefault(("fp", tag), set()).add("pending_candidate")
        for tag in seed - pending:
            diff_origins.setdefault(("fn", tag), set()).add("pending_candidate_removal")
        for tag in detected - pending:
            diff_origins.setdefault(("fp", tag), set()).add("current_run")
        for tag in seed - detected:
            diff_origins.setdefault(("fn", tag), set()).add("current_run")
        for (kind, tag), origins in sorted(diff_origins.items()):
            key = (case_id, tag, kind)
            old = prior.get(key, {})
            transcript_hash = str(gold.get("transcript_hash") or "")
            context_fingerprint = audit_context_fingerprint(
                case_id=case_id,
                tag=tag,
                kind=kind,
                expected_tags=sorted(seed),
                detected_tags=sorted(detected),
                seed_tags=sorted(seed),
                pending_tags=sorted(pending),
                transcript_hash=transcript_hash,
                tag_gold_fingerprint=gold_fps["tag_gold_fingerprint"],
                tag_seed_fingerprint=seed_fingerprint,
            )
            preserve_review = bool(
                old.get("context_fingerprint") == context_fingerprint
                and old.get("review_status") == "human_reviewed"
                and old.get("reviewer")
            )
            preserve_proposal = old.get("context_fingerprint") == context_fingerprint
            rows.append({
                "audit_schema_version": 2,
                "case_id": case_id,
                "tag": tag,
                "kind": kind,
                "quality": gold.get("quality"),
                "gold_note": gold.get("note"),
                "expected_tags": sorted(seed),
                "seed_expected_tags": sorted(seed),
                "pending_tags": sorted(pending),
                "detected_tags": sorted(detected),
                "origins": sorted(origins),
                "transcript": _transcript_excerpt(gold),
                "transcript_hash": transcript_hash,
                "source_report_fingerprint": source_report_fingerprint,
                "source_score_gold_fingerprint": gold_fps["score_gold_fingerprint"],
                "source_tag_gold_fingerprint": gold_fps["tag_gold_fingerprint"],
                "source_tag_seed_fingerprint": seed_fingerprint,
                "context_fingerprint": context_fingerprint,
                "proposed_verdict": old.get("proposed_verdict", "") if preserve_proposal else "",
                "proposal_note": old.get("proposal_note", "") if preserve_proposal else "",
                "verdict": old.get("verdict", "") if preserve_review else "",
                "note": old.get("note", "") if preserve_review else "",
                "review_status": "human_reviewed" if preserve_review else "pending",
                "reviewer": old.get("reviewer", "") if preserve_review else "",
                "reviewed_at": old.get("reviewed_at", "") if preserve_review else "",
            })
            if kind == "fp":
                n_fp += 1
            else:
                n_fn += 1

    OUT.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    cases_with_diffs = len({r["case_id"] for r in rows})
    empty_gold = sum(1 for tc in tag_cases if not tc.get("expected_tags"))
    print(
        f"tag audit: {len(rows)} diff rows (fp={n_fp}, fn={n_fn}) across "
        f"{cases_with_diffs}/{len(tag_cases)} cases -> {OUT}"
    )
    print(f"gold cases with EMPTY expected_weak_tags: {empty_gold}/{len(tag_cases)}")


if __name__ == "__main__":
    main()
