"""Fingerprints and validation for scorer annotation audits."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

TAG_STATUS_PENDING = "pending"
TAG_STATUS_HUMAN_EXHAUSTIVE = "human_reviewed_exhaustive_v1"


def stable_fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scorer_gold_fingerprints(cases: list[dict[str, Any]]) -> dict[str, str]:
    """Keep score-band and tag annotations independently versioned."""
    ordered = sorted(cases, key=lambda case: str(case.get("id", "")))
    score_payload = [
        {
            "id": case.get("id"),
            "scene_id": case.get("scene_id"),
            "dialog_pairs": case.get("dialog_pairs") or [],
            "expected_score_range": case.get("expected_score_range"),
            "strict_score_range": case.get("strict_score_range"),
            "quality": case.get("quality"),
            "band_status": case.get("band_status"),
            "transcript_hash": case.get("transcript_hash"),
        }
        for case in ordered
    ]
    tag_payload = [
        {
            "id": case.get("id"),
            "transcript_hash": case.get("transcript_hash"),
            "expected_weak_tags": sorted(case.get("expected_weak_tags") or []),
            "tag_status": case.get("tag_status"),
        }
        for case in ordered
    ]
    return {
        "score_gold_fingerprint": stable_fingerprint(score_payload),
        "tag_gold_fingerprint": stable_fingerprint(tag_payload),
    }


def tag_seed_fingerprint(seed_tags_by_id: dict[str, list[str]]) -> str:
    return stable_fingerprint({
        case_id: sorted(tags)
        for case_id, tags in sorted(seed_tags_by_id.items())
    })


def audit_context_fingerprint(
    *,
    case_id: str,
    tag: str,
    kind: str,
    expected_tags: list[str],
    detected_tags: list[str],
    seed_tags: list[str],
    pending_tags: list[str],
    transcript_hash: str,
    tag_gold_fingerprint: str,
    tag_seed_fingerprint: str,
) -> str:
    return stable_fingerprint({
        "case_id": case_id,
        "tag": tag,
        "kind": kind,
        "expected_tags": sorted(expected_tags),
        "detected_tags": sorted(detected_tags),
        "seed_tags": sorted(seed_tags),
        "pending_tags": sorted(pending_tags),
        "transcript_hash": transcript_hash,
        "tag_gold_fingerprint": tag_gold_fingerprint,
        "tag_seed_fingerprint": tag_seed_fingerprint,
    })


def validate_tag_audit_source(
    report: dict[str, Any],
    gold_cases: list[dict[str, Any]],
) -> list[str]:
    """Reject subset, fallback, stale, or structurally incomplete reports."""
    details = report.get("details") or {}
    tag_cases = details.get("tag_case_results") or []
    errors: list[str] = []
    expected_ids = {str(case.get("id")) for case in gold_cases}
    report_ids = {str(case.get("id")) for case in tag_cases}
    method_dist = details.get("scorer_method_distribution") or {}
    method_total = sum(int(count) for count in method_dist.values())
    current_fps = scorer_gold_fingerprints(gold_cases)

    if report.get("stage") != "scorer_transcript":
        errors.append("report stage must be scorer_transcript")
    if details.get("selected_case_ids"):
        errors.append("subset scorer reports cannot seed a tag audit")
    if details.get("total_cases") != len(gold_cases) or report_ids != expected_ids:
        errors.append("report case set does not match the current full gold set")
    if len(tag_cases) != len(gold_cases):
        errors.append("report must include one tag_case_results row per gold case")
    if details.get("transcript_integrity_pass") != 1.0:
        errors.append("report transcript_integrity_pass must equal 1.0")
    if method_total != len(gold_cases) or any(
        not str(method).startswith("llm_scorer") for method in method_dist
    ):
        errors.append("report must be a complete LLM-only scorer run")
    if details.get("tag_gold_fingerprint") != current_fps["tag_gold_fingerprint"]:
        errors.append("report tag gold fingerprint is missing or stale")
    return errors
