"""Mark legacy auto-approved tag labels as pending review."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.audit_provenance import TAG_STATUS_PENDING

GOLD = Path("data/eval/scorer_transcript_gold.jsonl")


def main() -> None:
    rows = [
        json.loads(line)
        for line in GOLD.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    changed = 0
    for row in rows:
        if row.get("tag_status") == "exhaustive_v1":
            row["tag_status"] = TAG_STATUS_PENDING
            changed += 1
    GOLD.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Marked {changed}/{len(rows)} scorer tag rows as {TAG_STATUS_PENDING}")


if __name__ == "__main__":
    main()
