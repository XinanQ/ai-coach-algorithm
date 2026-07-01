"""Auto-generate retrieval gold data from scoring criteria and customer profiles.

Tutor route: query = must_points joined, gold = source_chunk_ids
Customer route: query = opening_question, gold = chunks sharing scene_id with criteria
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.file_loader import read_json

CRITERIA_PATH = "data/marketing_scoring_criteria.json"
PROFILES_PATH = "data/customer_profiles.json"
CHUNKS_PATH = "data/marketing_chunks.json"
OUTPUT_PATH = Path("data/eval/retrieval_gold.jsonl")


def _load_criteria() -> list[dict[str, Any]]:
    data = read_json(CRITERIA_PATH, default={})
    return data.get("criteria", []) if isinstance(data, dict) else []


def _load_chunks() -> list[dict[str, Any]]:
    data = read_json(CHUNKS_PATH, default={})
    if isinstance(data, dict):
        return data.get("chunks", [])
    return data or []


def _load_profiles() -> list[dict[str, Any]]:
    return read_json(PROFILES_PATH, default=[]) or []


def build() -> list[dict[str, Any]]:
    criteria = _load_criteria()
    profiles = _load_profiles()
    chunks = _load_chunks()

    chunks_by_scene: dict[str, list[str]] = {}
    for chunk in chunks:
        sid = chunk.get("scene_id", "")
        cid = chunk.get("chunk_id", "")
        if sid and cid:
            chunks_by_scene.setdefault(sid, []).append(cid)

    rows: list[dict[str, Any]] = []

    for c in criteria:
        if not c.get("enabled", True):
            continue
        source_ids = c.get("source_chunk_ids", [])
        if not source_ids:
            continue
        must_points = c.get("must_points", [])
        query = "；".join(must_points) if must_points else c.get("answer_goal", "")
        rows.append({
            "id": f"RG_tutor_{c['criterion_id']}",
            "route": "tutor",
            "query": query,
            "scene_id": c.get("scene_id"),
            "gold_chunk_ids": source_ids,
            "source": "criteria",
            "criterion_id": c["criterion_id"],
        })

    for p in profiles:
        scene_id = p.get("scene_id", "")
        question = p.get("opening_question", "")
        if not question or not scene_id:
            continue
        gold_ids = chunks_by_scene.get(scene_id, [])
        if not gold_ids:
            continue
        rows.append({
            "id": f"RG_customer_{p['customer_id']}",
            "route": "customer",
            "query": question,
            "scene_id": scene_id,
            "gold_chunk_ids": gold_ids,
            "source": "profile",
            "customer_id": p["customer_id"],
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
    tutor = sum(1 for r in rows if r["route"] == "tutor")
    customer = sum(1 for r in rows if r["route"] == "customer")
    print(f"Generated {count} retrieval gold rows: {tutor} tutor + {customer} customer")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
