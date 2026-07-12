"""Create the immutable scorer tag-review seed from the original E2E labels."""
from __future__ import annotations

import json
from pathlib import Path

SOURCE = Path("data/eval/e2e_dialog_gold.jsonl")
OUT = Path("data/eval/scorer_tag_review_seed.jsonl")


def main() -> None:
    if OUT.exists():
        raise SystemExit(f"refusing to overwrite frozen seed: {OUT}")
    rows = []
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            source = json.loads(line)
            rows.append({
                "id": f"scorer_{source['id']}",
                "expected_weak_tags": source.get("expected_weak_tags") or [],
            })
    OUT.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"Created frozen tag-review seed with {len(rows)} cases: {OUT}")


if __name__ == "__main__":
    main()
