"""Normalize an annotation file into train/eval splits for intent modeling.

Works *now* with placeholder data: rows that are not yet human-reviewed fall
back to `suggested_labels`, so the whole pipeline runs end to end before gold
exists. Once a row is annotated (`needs_review: false`), its `gold_labels`
become authoritative — including an empty list (a valid negative sample).
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from app.core.intent_labels import INTENT_LABELS
from app.utils.file_loader import resolve_path


DEFAULT_INPUT = "data/intent_eval_candidates.jsonl"
DEFAULT_TRAIN = "data/intent_train.jsonl"
DEFAULT_EVAL = "data/intent_eval.jsonl"


def _read_jsonl(path: str) -> list[dict[str, Any]]:
    file_path = resolve_path(path)
    if not file_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _labels_for_row(row: dict[str, Any]) -> tuple[list[str], bool]:
    """Return (labels, is_gold). Reviewed rows use gold_labels; others fall back."""
    reviewed = row.get("needs_review") is False
    if reviewed:
        labels = row.get("gold_labels") or []
        is_gold = True
    else:
        labels = row.get("suggested_labels") or row.get("gold_labels") or []
        is_gold = False
    labels = [label for label in INTENT_LABELS if label in set(labels)]
    return labels, is_gold


def load_labeled_rows(path: str = DEFAULT_INPUT) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _read_jsonl(path):
        text = str(row.get("text", "")).strip()
        if not text:
            continue
        labels, is_gold = _labels_for_row(row)
        rows.append({"text": text, "labels": labels, "is_gold": is_gold, "id": row.get("id")})
    return rows


def split_train_eval(
    rows: list[dict[str, Any]],
    eval_ratio: float = 0.3,
    seed: int = 13,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    shuffled = rows[:]
    random.Random(seed).shuffle(shuffled)
    eval_size = max(1, int(len(shuffled) * eval_ratio)) if shuffled else 0
    return shuffled[eval_size:], shuffled[:eval_size]


def _write(rows: list[dict[str, Any]], path: str) -> Path:
    out = resolve_path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(json.dumps({"text": r["text"], "labels": r["labels"]}, ensure_ascii=False) for r in rows) + "\n"
        if rows
        else "",
        encoding="utf-8",
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Split an intent annotation file into train/eval sets.")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--train-out", default=DEFAULT_TRAIN)
    parser.add_argument("--eval-out", default=DEFAULT_EVAL)
    parser.add_argument("--eval-ratio", type=float, default=0.3)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    rows = load_labeled_rows(args.input)
    gold_count = sum(1 for r in rows if r["is_gold"])
    train, eval_rows = split_train_eval(rows, eval_ratio=args.eval_ratio, seed=args.seed)
    _write(train, args.train_out)
    _write(eval_rows, args.eval_out)
    print(
        json.dumps(
            {
                "input": args.input,
                "total": len(rows),
                "gold_reviewed": gold_count,
                "placeholder_rows": len(rows) - gold_count,
                "train_size": len(train),
                "eval_size": len(eval_rows),
                "train_out": args.train_out,
                "eval_out": args.eval_out,
                "warning": None if gold_count else "No reviewed gold rows yet — using suggested_labels as PLACEHOLDER. Numbers are pipeline smoke-test only.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
