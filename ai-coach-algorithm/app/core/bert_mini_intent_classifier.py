from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from app.core.customer_answer_understanding import keyword_intent_scores
from app.core.intent_labels import INTENT_LABELS
from app.core.text_cleaner import clean_text
from app.utils.file_loader import resolve_path


DEFAULT_INTENT_MODEL_DIR = "models/bert_mini_intent"


@dataclass
class BertMiniPrediction:
    available: bool
    model_dir: str
    labels: list[str]
    scores: dict[str, float]
    threshold: float
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "model_dir": self.model_dir,
            "labels": self.labels,
            "scores": self.scores,
            "threshold": self.threshold,
            "fallback_reason": self.fallback_reason,
        }


class BertMiniIntentClassifier:
    """Inference wrapper for a fine-tuned BERT-mini multi-label classifier."""

    def __init__(
        self,
        model_dir: str | None = None,
        threshold: float | None = None,
        local_files_only: bool | None = None,
    ) -> None:
        self.model_dir = model_dir or os.getenv("AI_COACH_BERT_MINI_INTENT_DIR") or DEFAULT_INTENT_MODEL_DIR
        self.threshold = threshold if threshold is not None else float(os.getenv("AI_COACH_BERT_MINI_THRESHOLD", "0.5"))
        self.available = False
        self.fallback_reason: str | None = None
        self.labels = INTENT_LABELS[:]
        self.tokenizer = None
        self.model = None
        self.torch = None
        if local_files_only is None:
            local_files_only = os.getenv("AI_COACH_MODEL_LOCAL_ONLY", "0") == "1"

        model_path = resolve_path(self.model_dir)
        label_path = model_path / "label_mapping.json"
        try:
            if not model_path.exists():
                raise FileNotFoundError(f"fine-tuned model dir not found: {model_path}")
            if label_path.exists():
                data = json.loads(label_path.read_text(encoding="utf-8"))
                self.labels = list(data.get("labels") or self.labels)
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self.torch = torch
            self.tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=local_files_only)
            self.model = AutoModelForSequenceClassification.from_pretrained(str(model_path), local_files_only=local_files_only)
            self.model.eval()
            self.available = True
        except Exception as exc:
            self.fallback_reason = f"{type(exc).__name__}: {exc}"[:500]

    def predict(self, text: str) -> BertMiniPrediction:
        if not self.available:
            scores = keyword_intent_scores(text)
            labels = [label for label, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if score > 0]
            return BertMiniPrediction(
                available=False,
                model_dir=self.model_dir,
                labels=labels[:5],
                scores=scores,
                threshold=self.threshold,
                fallback_reason=self.fallback_reason,
            )

        assert self.tokenizer is not None
        assert self.model is not None
        assert self.torch is not None
        inputs = self.tokenizer(
            clean_text(text),
            truncation=True,
            max_length=160,
            padding=True,
            return_tensors="pt",
        )
        with self.torch.no_grad():
            logits = self.model(**inputs).logits[0]
            probs = self.torch.sigmoid(logits).cpu().tolist()
        scores = {label: round(float(score), 4) for label, score in zip(self.labels, probs)}
        labels = [label for label, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if score >= self.threshold]
        return BertMiniPrediction(
            available=True,
            model_dir=self.model_dir,
            labels=labels,
            scores=scores,
            threshold=self.threshold,
        )


_CLASSIFIER_CACHE: dict[tuple[str | None, float | None], BertMiniIntentClassifier] = {}


def get_bert_mini_intent_classifier(
    model_dir: str | None = None,
    threshold: float | None = None,
) -> BertMiniIntentClassifier:
    key = (model_dir, threshold)
    if key not in _CLASSIFIER_CACHE:
        _CLASSIFIER_CACHE[key] = BertMiniIntentClassifier(model_dir=model_dir, threshold=threshold)
    return _CLASSIFIER_CACHE[key]


def reset_bert_mini_intent_classifier_cache() -> None:
    _CLASSIFIER_CACHE.clear()

