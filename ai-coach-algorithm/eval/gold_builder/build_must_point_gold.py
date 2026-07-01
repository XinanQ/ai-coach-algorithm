"""Semi-auto must-point coverage gold data builder.

Selects representative criteria, generates template employee answers at
different quality levels, and labels each must_point as covered/missing.
Human review is required before using as gold.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.file_loader import read_json

CRITERIA_PATH = "data/marketing_scoring_criteria.json"
OUTPUT_PATH = Path("data/eval/must_point_coverage_gold.jsonl")


def _load_criteria() -> list[dict[str, Any]]:
    data = read_json(CRITERIA_PATH, default={})
    return data.get("criteria", []) if isinstance(data, dict) else []


def _generate_good_answer(must_points: list[str], key_terms: list[str]) -> str:
    parts = []
    for mp in must_points[:5]:
        parts.append(f"关于{mp[:15]}，我来给您详细说明一下。")
    if key_terms:
        parts.append(f"关键要注意{'、'.join(key_terms[:3])}方面的问题。")
    return "".join(parts)


def _generate_partial_answer(must_points: list[str]) -> str:
    if len(must_points) <= 1:
        return f"我简单说一下，{must_points[0][:20]}这个方面很重要。"
    return f"我先说一下，{must_points[0][:20]}，另外{must_points[1][:20]}也要注意。"


def _generate_poor_answer() -> str:
    return "您好，这个产品挺好的，很多客户都买了，您要不要也了解一下？"


def build(max_criteria: int = 15) -> list[dict[str, Any]]:
    criteria = _load_criteria()
    criteria = [c for c in criteria if c.get("enabled", True) and c.get("must_points")]
    criteria = criteria[:max_criteria]

    rows: list[dict[str, Any]] = []

    for c in criteria:
        cid = c["criterion_id"]
        must_points = c["must_points"]
        key_terms = c.get("key_terms", [])

        # Good answer: covers ~all must_points
        good_answer = _generate_good_answer(must_points, key_terms)
        rows.append({
            "id": f"MPG_good_{cid}",
            "criterion_id": cid,
            "scene_id": c.get("scene_id"),
            "employee_answer": good_answer,
            "must_points": must_points,
            "key_terms": key_terms,
            "gold_covered_points": must_points[:5],
            "gold_missing_points": must_points[5:],
            "quality": "good",
            "needs_review": True,
        })

        # Partial answer: covers ~2 must_points
        partial_answer = _generate_partial_answer(must_points)
        rows.append({
            "id": f"MPG_partial_{cid}",
            "criterion_id": cid,
            "scene_id": c.get("scene_id"),
            "employee_answer": partial_answer,
            "must_points": must_points,
            "key_terms": key_terms,
            "gold_covered_points": must_points[:2],
            "gold_missing_points": must_points[2:],
            "quality": "partial",
            "needs_review": True,
        })

        # Poor answer: covers nothing
        poor_answer = _generate_poor_answer()
        rows.append({
            "id": f"MPG_poor_{cid}",
            "criterion_id": cid,
            "scene_id": c.get("scene_id"),
            "employee_answer": poor_answer,
            "must_points": must_points,
            "key_terms": key_terms,
            "gold_covered_points": [],
            "gold_missing_points": must_points,
            "quality": "poor",
            "needs_review": True,
        })

    return rows


def save(rows: list[dict[str, Any]] | None = None, path: Path = OUTPUT_PATH) -> int:
    if rows is None:
        rows = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def main() -> None:
    rows = build()
    count = save(rows)
    good = sum(1 for r in rows if r["quality"] == "good")
    partial = sum(1 for r in rows if r["quality"] == "partial")
    poor = sum(1 for r in rows if r["quality"] == "poor")
    print(f"Generated {count} must-point gold rows: {good} good + {partial} partial + {poor} poor")
    print(f"Saved to {OUTPUT_PATH}")
    print("NOTE: All rows have needs_review=True — manually verify before using as gold.")


if __name__ == "__main__":
    main()
