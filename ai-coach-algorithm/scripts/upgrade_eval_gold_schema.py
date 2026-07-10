"""Upgrade E2E route expectations and stamp reviewed fixed transcripts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from eval.evidence import customer_evidence_after_each_turn
from eval.transcript import transcript_hash


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    temp_path.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--e2e", type=Path, default=Path("data/eval/e2e_dialog_gold.jsonl"))
    parser.add_argument("--scorer", type=Path, default=Path("data/eval/scorer_transcript_gold.jsonl"))
    args = parser.parse_args()

    e2e_rows = _load_jsonl(args.e2e)
    for row in e2e_rows:
        row["evaluation_schema_version"] = 2
        row.setdefault("dynamic_score_band_status", "legacy_unbound")
        directions = list(row.get("expected_followup_direction") or [])
        row.setdefault("expected_customer_evidence", directions)
        evidence_status = str(row.get("customer_evidence_status") or "")
        if evidence_status != "reviewed":
            row["expected_customer_evidence_after_each_turn"] = customer_evidence_after_each_turn(directions)
            row["customer_evidence_status"] = "derived_v2"
        row.setdefault("expected_tutor_evidence", list(row.get("expected_must_points") or []))
    _write_jsonl(args.e2e, e2e_rows)

    scorer_rows = _load_jsonl(args.scorer)
    for row in scorer_rows:
        row["transcript_hash"] = transcript_hash(row.get("scene_id"), row.get("dialog_pairs") or [])
        if row.get("band_status") == "reviewed":
            row.setdefault("strict_score_range", list(row.get("expected_score_range") or [0, 100]))
    _write_jsonl(args.scorer, scorer_rows)

    print(f"Upgraded {len(e2e_rows)} dynamic E2E cases and {len(scorer_rows)} fixed scorer cases")


if __name__ == "__main__":
    main()
