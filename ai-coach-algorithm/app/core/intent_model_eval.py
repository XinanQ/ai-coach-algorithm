"""Evaluate intent prediction on a held-out eval set: keyword baseline vs BERT-mini.

This is the scoreboard for the BERT-mini P1: it reports whether the fine-tuned
classifier actually beats the keyword baseline on gold data. Runs now with
placeholder labels (smoke test); becomes meaningful after annotation + training.
"""
from __future__ import annotations

import argparse
import json

from app.core.bert_mini_intent_classifier import get_bert_mini_intent_classifier
from app.core.customer_answer_understanding import keyword_intent_scores
from app.core.intent_dataset_prep import DEFAULT_EVAL, _read_jsonl
from app.core.intent_labels import INTENT_LABELS
from app.core.intent_metrics import multilabel_prf1


def _load_eval(path: str) -> list[dict[str, object]]:
    rows = []
    for row in _read_jsonl(path):
        text = str(row.get("text", "")).strip()
        if text:
            rows.append({"text": text, "labels": [l for l in INTENT_LABELS if l in set(row.get("labels", []))]})
    return rows


def _keyword_pred(text: str, threshold: float) -> set[str]:
    scores = keyword_intent_scores(text)
    return {label for label, score in scores.items() if score >= threshold}


def evaluate(eval_path: str, keyword_threshold: float) -> dict[str, object]:
    rows = _load_eval(eval_path)
    if not rows:
        return {"error": f"no eval rows at {eval_path}; run intent_dataset_prep first"}
    gold_sets = [set(r["labels"]) for r in rows]

    keyword_preds = [_keyword_pred(str(r["text"]), keyword_threshold) for r in rows]
    keyword_metrics = multilabel_prf1(gold_sets, keyword_preds)

    classifier = get_bert_mini_intent_classifier()
    bert_block: dict[str, object]
    if classifier.available:
        bert_preds = [set(classifier.predict(str(r["text"])).labels) for r in rows]
        bert_block = {"available": True, "metrics": multilabel_prf1(gold_sets, bert_preds)}
    else:
        bert_block = {
            "available": False,
            "reason": classifier.fallback_reason,
            "note": "Train with bert_mini_trainer (model dir: models/bert_mini_intent) then re-run.",
        }

    return {
        "eval_size": len(rows),
        "keyword_baseline": {"threshold": keyword_threshold, "metrics": keyword_metrics},
        "bert_mini": bert_block,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare keyword baseline vs BERT-mini on the intent eval set.")
    parser.add_argument("--eval", default=DEFAULT_EVAL)
    parser.add_argument("--keyword-threshold", type=float, default=0.05)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.eval, args.keyword_threshold), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
