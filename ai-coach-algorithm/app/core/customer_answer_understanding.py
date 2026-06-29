from __future__ import annotations

import os

from app.core.intent_labels import INTENT_KEYWORDS
from app.core.text_cleaner import clean_text


# Gate BERT-mini fusion behind an env flag. The current trained model collapses
# to all-zeros on the eval set (peak val F1 0.23 at epoch 2, then drops to 0
# by epoch 5, and the trainer saves the last epoch). Keyword baseline alone
# scores micro_f1 ~0.58, so fusing in a broken BERT actively hurts. When the
# model is retrained to actually beat keyword, flip this to "1" — no code change.
_BERT_MINI_FUSION_ENABLED = os.getenv("AI_COACH_BERT_MINI_FUSION", "0") == "1"


def keyword_intent_scores(text: str) -> dict[str, float]:
    value = clean_text(text)
    scores: dict[str, float] = {}
    for label, keywords in INTENT_KEYWORDS.items():
        hit = sum(1 for keyword in keywords if keyword in value)
        scores[label] = round(hit / max(len(keywords), 1), 4)
    return scores


def analyze_customer_answer(text: str) -> dict[str, object]:
    from app.core.bert_mini_intent_classifier import get_bert_mini_intent_classifier

    cleaned = clean_text(text)
    keyword_scores = keyword_intent_scores(text)
    classifier = get_bert_mini_intent_classifier()
    prediction = classifier.predict(text)
    bert_scores = prediction.scores

    if prediction.available and _BERT_MINI_FUSION_ENABLED:
        fused = {
            label: round(0.70 * bert_scores.get(label, 0.0) + 0.30 * keyword_scores.get(label, 0.0), 4)
            for label in set(keyword_scores) | set(bert_scores)
        }
        method = "bert_mini_classifier_with_keyword_fusion"
    else:
        fused = {
            label: round(float(keyword_scores.get(label, 0.0)), 4)
            for label in keyword_scores
        }
        method = (
            "keyword_baseline_bert_mini_disabled"
            if prediction.available
            else "keyword_baseline_with_bert_mini_fallback"
        )

    labels = [label for label, score in sorted(fused.items(), key=lambda item: item[1], reverse=True) if score > 0]
    return {
        "text": cleaned,
        "intent_labels": labels[:5],
        "intent_scores": fused,
        "keyword_intent_scores": keyword_scores,
        "bert_mini_available": prediction.available,
        "bert_mini_scores": bert_scores,
        "risk_flags": [label for label in labels if label == "compliance_sensitive"],
        "method": method,
    }
