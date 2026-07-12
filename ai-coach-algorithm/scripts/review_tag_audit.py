"""Record one explicit human verdict in the weak-tag audit."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

AUDIT = Path("data/eval/tag_audit.jsonl")
VALID = {
    "fp": {"justified", "spurious"},
    "fn": {"detector_miss", "gold_wrong"},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--kind", choices=sorted(VALID), required=True)
    parser.add_argument("--verdict", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--note", required=True)
    args = parser.parse_args()

    if args.verdict not in VALID[args.kind]:
        raise SystemExit(
            f"invalid verdict {args.verdict!r} for {args.kind}; "
            f"choose one of {sorted(VALID[args.kind])}"
        )
    if not args.reviewer.strip() or not args.note.strip():
        raise SystemExit("reviewer and note must be non-empty")
    rows = [
        json.loads(line)
        for line in AUDIT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    matches = [
        row for row in rows
        if row.get("case_id") == args.case_id
        and row.get("tag") == args.tag
        and row.get("kind") == args.kind
    ]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one audit row, found {len(matches)}")
    row = matches[0]
    if row.get("audit_schema_version") != 2 or not row.get("context_fingerprint"):
        raise SystemExit("audit row lacks v2 provenance; rebuild from a fresh scorer report first")
    row["verdict"] = args.verdict
    row["note"] = args.note.strip()
    row["review_status"] = "human_reviewed"
    row["reviewer"] = args.reviewer.strip()
    row["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    AUDIT.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Reviewed {args.case_id} / {args.kind} / {args.tag}: {args.verdict}")


if __name__ == "__main__":
    main()
