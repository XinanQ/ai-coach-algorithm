"""Build a human-annotation candidate set for intent labels.

This is the shared evaluation linchpin for two P1 tasks:
  1. Calibrating coverage thresholds (intent gap + must_point).
  2. Training / evaluating the BERT-mini intent classifier.

Unlike `intent_training_data_builder` (which auto-generates *weak* labels for
bootstrapping training), this sampler pulls **natural** utterances from real
data sources, deduplicates and stratifies them, pre-fills keyword-based
`suggested_labels` only as a hint, and leaves `gold_labels` EMPTY for a human to
fill. The corrected file becomes the held-out gold eval/train set.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.customer_answer_understanding import keyword_intent_scores
from app.core.intent_labels import INTENT_LABELS
from app.core.text_cleaner import clean_text
from app.utils.file_loader import read_json, resolve_path


DEFAULT_OUTPUT = "data/intent_eval_candidates.jsonl"
MIN_LEN = 6
MAX_LEN = 200


def _suggested_labels(text: str) -> list[str]:
    scores = keyword_intent_scores(text)
    return [label for label in INTENT_LABELS if scores.get(label, 0.0) > 0]


def _gather_candidates() -> list[dict[str, Any]]:
    """Collect natural utterances from real data, tagged with channel/source."""
    candidates: list[dict[str, Any]] = []

    def add(text: Any, channel: str, source: str, scene_id: str | None = None) -> None:
        value = clean_text(str(text))
        if MIN_LEN <= len(value) <= MAX_LEN:
            candidates.append({"text": value, "channel": channel, "source": source, "scene_id": scene_id})

    # Customer-side utterances from profiles.
    for profile in read_json("data/customer_profiles.json", default=[]) or []:
        scene = profile.get("scene_id")
        add(profile.get("opening_question", ""), "customer", "customer_profiles.opening_question", scene)
        add(profile.get("concern", ""), "customer", "customer_profiles.concern", scene)

    # Customer-side utterances from chunks (queries + customer view).
    chunks_data = read_json("data/marketing_chunks.json", default={}) or {}
    chunks = chunks_data.get("chunks", []) if isinstance(chunks_data, dict) else chunks_data
    for chunk in chunks if isinstance(chunks, list) else []:
        scene = chunk.get("scene_id")
        add(chunk.get("customer_query", ""), "customer", "marketing_chunks.customer_query", scene)
        for query in chunk.get("customer_queries") or []:
            add(query, "customer", "marketing_chunks.customer_queries", scene)
        add(chunk.get("customer_view_text", ""), "customer", "marketing_chunks.customer_view_text", scene)

    # Real dialogue turns from long-term memory (both speakers).
    for memory in read_json("mock_db/longterm_memory.json", default=[]) or []:
        scene = memory.get("scenario_id") or memory.get("scene_id")
        for message in memory.get("messages", []):
            channel = "employee" if message.get("role") == "employee" else "customer"
            add(message.get("content", ""), channel, f"longterm_memory.{message.get('role')}", scene)

    return candidates


def build_eval_candidates(target_size: int = 250, seed: int = 7) -> list[dict[str, Any]]:
    raw = _gather_candidates()

    # Deduplicate by normalized text.
    by_text: dict[str, dict[str, Any]] = {}
    for item in raw:
        by_text.setdefault(item["text"], item)
    pool = list(by_text.values())

    rng = random.Random(seed)
    rng.shuffle(pool)

    # Stratify: make sure each label has some representation before filling the
    # rest, so rare intents are not crowded out by the common ones.
    per_label_target = max(1, target_size // (len(INTENT_LABELS) * 2))
    label_counts: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    leftovers: list[dict[str, Any]] = []

    for item in pool:
        suggested = _suggested_labels(item["text"])
        item["suggested_labels"] = suggested
        if suggested and any(label_counts[label] < per_label_target for label in suggested):
            selected.append(item)
            for label in suggested:
                label_counts[label] += 1
        else:
            leftovers.append(item)
        if len(selected) >= target_size:
            break

    for item in leftovers:
        if len(selected) >= target_size:
            break
        selected.append(item)

    ordered = selected[:target_size]
    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(ordered, start=1):
        rows.append(
            {
                "id": f"IE_{idx:04d}",
                "text": item["text"],
                "channel": item["channel"],
                "scene_id": item.get("scene_id"),
                "source": item["source"],
                "suggested_labels": item.get("suggested_labels", []),
                "gold_labels": [],
                "needs_review": True,
            }
        )
    return rows


def write_jsonl(rows: list[dict[str, Any]], output_path: str = DEFAULT_OUTPUT) -> Path:
    path = resolve_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample natural utterances into an intent annotation candidate set.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--target-size", type=int, default=250)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rows = build_eval_candidates(target_size=args.target_size, seed=args.seed)
    path = write_jsonl(rows, args.output)
    channel_counts = Counter(row["channel"] for row in rows)
    suggested_counts = Counter(label for row in rows for label in row["suggested_labels"])
    print(
        json.dumps(
            {
                "output": str(path),
                "count": len(rows),
                "by_channel": channel_counts,
                "suggested_label_distribution": suggested_counts,
                "note": "gold_labels are empty by design — fill them by human review.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
