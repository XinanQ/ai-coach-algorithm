"""Rewrite scorer gold expected_weak_tags to the exhaustive set per the tag audit.

Reads data/eval/tag_audit.jsonl. AI proposals from
apply_tag_audit_verdicts.py are not sufficient: every row must have an
explicit human verdict, reviewer, and matching provenance. Per case it:
  + adds every fp tag judged `justified` (weakness truly present, gold missed it)
  - removes every fn tag judged `gold_wrong`
  = keeps fn tags judged `detector_miss` (real misses must keep failing)
Existing tags are normalized to canonical taxonomy IDs (aliases like 合规风险/
成交引导不足/风险说明缺失 map through app.core.weakness_taxonomy — matching
behavior is unchanged, the stored form just becomes canonical).

Marks every case with tag_status="human_reviewed_exhaustive_v1" and flips the
suite's tag contract to citable exhaustive labels. Does NOT
touch dialog_pairs / transcript_hash / score bands — the frozen 0.92–0.94
baseline is unaffected.

Single-shot by design: a successful apply rewrites the gold, which changes the
tag gold fingerprint, so a second run is rejected by the provenance check.
To redo the work, rebuild the audit from a fresh full report and re-review.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.weakness_taxonomy import normalize_weakness_tag, normalize_weakness_tags
from eval.audit_provenance import (
    TAG_STATUS_HUMAN_EXHAUSTIVE,
    audit_context_fingerprint,
    scorer_gold_fingerprints,
    tag_seed_fingerprint,
)

AUDIT = Path("data/eval/tag_audit.jsonl")
GOLD = Path("data/eval/scorer_transcript_gold.jsonl")
SEED_GOLD = Path("data/eval/scorer_tag_review_seed.jsonl")


def _load_seed_tags() -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for line in SEED_GOLD.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["id"]] = normalize_weakness_tags(row.get("expected_weak_tags"))
    return rows


def main() -> None:
    add: dict[str, set[str]] = defaultdict(set)
    remove: dict[str, set[str]] = defaultdict(set)
    audit_rows = []
    review_errors = []
    for line in AUDIT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        audit_rows.append(row)
        verdict = row.get("verdict")
        valid_verdicts = {"justified", "spurious"} if row.get("kind") == "fp" else {
            "detector_miss", "gold_wrong"
        }
        if (
            row.get("review_status") != "human_reviewed"
            or not row.get("reviewer")
            or not row.get("reviewed_at")
            or not row.get("note")
            or verdict not in valid_verdicts
        ):
            review_errors.append(f"{row.get('case_id')}:{row.get('kind')}:{row.get('tag')}")
            continue
        tag = normalize_weakness_tag(row["tag"])
        if row["kind"] == "fp" and verdict == "justified":
            add[row["case_id"]].add(tag)
        elif row["kind"] == "fn" and verdict == "gold_wrong":
            remove[row["case_id"]].add(tag)
    if review_errors:
        raise SystemExit(
            f"{len(review_errors)} audit rows are not explicitly human-reviewed; "
            f"first examples: {', '.join(review_errors[:5])}"
        )

    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    current_tag_fingerprint = scorer_gold_fingerprints(rows)["tag_gold_fingerprint"]
    seed_tags_by_id = _load_seed_tags()
    seed_fingerprint = tag_seed_fingerprint(seed_tags_by_id)
    if set(seed_tags_by_id) != {str(row.get("id")) for row in rows}:
        raise SystemExit("tag review seed case set does not match scorer gold")
    source_fingerprints = {row.get("source_tag_gold_fingerprint") for row in audit_rows}
    if source_fingerprints != {current_tag_fingerprint}:
        raise SystemExit(
            "audit provenance does not match the current tag gold; rebuild the audit from a fresh full report"
        )
    report_fingerprints = {row.get("source_report_fingerprint") for row in audit_rows}
    if len(report_fingerprints) != 1 or not next(iter(report_fingerprints), None):
        raise SystemExit("audit rows do not share one valid source report fingerprint")
    seed_fingerprints = {row.get("source_tag_seed_fingerprint") for row in audit_rows}
    if seed_fingerprints != {seed_fingerprint}:
        raise SystemExit("audit tag seed fingerprint is missing or stale")
    gold_by_id = {str(row.get("id")): row for row in rows}
    invalid_context = []
    for row in audit_rows:
        gold_case = gold_by_id.get(str(row.get("case_id")), {})
        expected_context = audit_context_fingerprint(
            case_id=str(row.get("case_id")),
            tag=str(row.get("tag")),
            kind=str(row.get("kind")),
            expected_tags=list(row.get("expected_tags") or []),
            detected_tags=list(row.get("detected_tags") or []),
            seed_tags=list(row.get("seed_expected_tags") or []),
            pending_tags=list(row.get("pending_tags") or []),
            transcript_hash=str(gold_case.get("transcript_hash") or ""),
            tag_gold_fingerprint=current_tag_fingerprint,
            tag_seed_fingerprint=seed_fingerprint,
        )
        if (
            row.get("audit_schema_version") != 2
            or row.get("transcript_hash") != gold_case.get("transcript_hash")
            or row.get("context_fingerprint") != expected_context
        ):
            invalid_context.append(f"{row.get('case_id')}:{row.get('kind')}:{row.get('tag')}")
    if invalid_context:
        raise SystemExit(
            f"{len(invalid_context)} audit rows have stale or edited judging context; "
            f"first examples: {', '.join(invalid_context[:5])}"
        )
    touched = added_total = removed_total = 0
    for case in rows:
        cid = case["id"]
        old = list(seed_tags_by_id[cid])
        new = [t for t in old if t not in remove.get(cid, set())]
        extra = sorted(add.get(cid, set()) - set(new))
        new = new + extra
        if new != (case.get("expected_weak_tags") or []):
            added_total += len(extra)
            removed_total += len(set(old) - set(new))
            case["expected_weak_tags"] = new
            touched += 1
        case["tag_status"] = TAG_STATUS_HUMAN_EXHAUSTIVE
    GOLD.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    empties = sum(1 for r in rows if not r.get("expected_weak_tags"))
    print(f"Gold tags {TAG_STATUS_HUMAN_EXHAUSTIVE}: {touched}/{len(rows)} cases changed, "
          f"+{added_total} tags added, -{removed_total} removed; "
          f"cases still with empty expected tags: {empties}")


if __name__ == "__main__":
    main()
