from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.customer_answer_understanding import keyword_intent_scores
from app.core.intent_labels import INTENT_KEYWORDS, INTENT_LABELS
from app.core.text_cleaner import clean_text
from app.utils.file_loader import read_json, resolve_path


DEFAULT_OUTPUT = "data/intent_training_samples.jsonl"


SEED_TEMPLATES = {
    "rate_concern": [
        "客户觉得别的银行利率更高，我会先认可客户关注收益，再说明利率以系统公示为准。",
        "客户问收益是不是最高，我不能承诺最高，只能帮他查询当前可办理利率。",
        "客户比较不同银行收益，我会引导他综合考虑安全、服务和到期管理。",
    ],
    "liquidity_concern": [
        "客户担心提前支取不方便，我会先了解资金什么时候可能要用。",
        "客户可能临时急用钱，我会建议保留部分活期，再安排短期限产品。",
        "客户说短期内可能要用，我会提醒期限选择要兼顾流动性。",
    ],
    "safety_concern": [
        "客户担心本金安全，我会说明产品风险和适配边界，不做保本承诺。",
        "客户问会不会亏，我会根据产品类型提示风险，并建议看正式材料。",
        "客户关注保障，我会解释清楚安全性、风险等级和适合人群。",
    ],
    "procedure_question": [
        "客户问怎么办理，我会说明需要带身份证和银行卡，并引导到网点查询。",
        "客户不清楚流程，我会说明办理步骤、材料和下一步确认方式。",
        "客户想查询当前产品，我会先帮他查系统信息，再确认是否继续办理。",
    ],
    "rejection_or_hesitation": [
        "客户说想再考虑，我会先理解他的顾虑，再询问主要担心哪一点。",
        "客户说要和家人商量，我会尊重他的决定，并补充可以带家人一起了解。",
        "客户暂时不用，我会询问原因并提供后续查询或预约方式。",
    ],
    "compliance_sensitive": [
        "如果员工说保证收益最高，这属于合规敏感表达。",
        "员工不能承诺稳赚，也不能说一定不会亏。",
        "客户追问能不能保证，我应该明确不能承诺收益，只能依据正式信息解释。",
    ],
}


def _labels_for_text(text: str) -> list[str]:
    scores = keyword_intent_scores(text)
    labels = [label for label in INTENT_LABELS if scores.get(label, 0.0) > 0]
    if "保证" in text or "承诺" in text or "稳赚" in text or "最高" in text:
        if "compliance_sensitive" not in labels:
            labels.append("compliance_sensitive")
    return labels


def _add_sample(samples: dict[str, dict[str, Any]], text: str, labels: list[str], source: str) -> None:
    value = clean_text(text)
    if len(value) < 8 or not labels:
        return
    key = value[:240]
    samples[key] = {
        "text": value[:500],
        "labels": [label for label in INTENT_LABELS if label in labels],
        "source": source,
        "weak_label": True,
    }


def build_intent_training_samples(target_size: int = 600) -> list[dict[str, Any]]:
    samples: dict[str, dict[str, Any]] = {}

    for label, texts in SEED_TEMPLATES.items():
        for text in texts:
            _add_sample(samples, text, [label], "seed_template")

    profiles = read_json("data/customer_profiles.json", default=[]) or []
    for profile in profiles if isinstance(profiles, list) else []:
        for field in ["opening_question", "concern", "followup_strategy", "personality"]:
            text = str(profile.get(field, ""))
            _add_sample(samples, text, _labels_for_text(text), f"customer_profiles.{field}")

    memories = read_json("mock_db/longterm_memory.json", default=[]) or []
    for memory in memories if isinstance(memories, list) else []:
        for message in memory.get("messages", []):
            text = str(message.get("content", ""))
            _add_sample(samples, text, _labels_for_text(text), "longterm_memory.messages")
        score_result = memory.get("score_result") or {}
        for key in ["answer_text_cleaned", "reference_script", "feedback"]:
            text = str(score_result.get(key) or memory.get(key) or "")
            _add_sample(samples, text, _labels_for_text(text), f"longterm_memory.{key}")

    chunks_data = read_json("data/marketing_chunks.json", default={}) or {}
    chunks = chunks_data.get("chunks", []) if isinstance(chunks_data, dict) else []
    for chunk in chunks:
        fields = [
            chunk.get("title", ""),
            chunk.get("customer_query", ""),
            " ".join(str(item) for item in (chunk.get("customer_queries") or [])),
            chunk.get("customer_view_text", ""),
            chunk.get("tutor_view_text", ""),
            chunk.get("content", ""),
        ]
        for text in fields:
            _add_sample(samples, str(text), _labels_for_text(str(text)), "marketing_chunks")

    # Balance weak labels by creating short, natural variants around label keywords.
    counts = Counter(label for sample in samples.values() for label in sample["labels"])
    round_id = 0
    while len(samples) < target_size:
        made_progress = False
        for label in INTENT_LABELS:
            keywords = INTENT_KEYWORDS[label]
            for keyword in keywords:
                text = f"客户提到{keyword}，员工需要识别这是{label}相关诉求，并给出合规、清晰的回应。"
                if label == "compliance_sensitive":
                    text = f"员工如果提到{keyword}，需要识别为合规敏感风险，不能做收益或安全承诺。"
                _add_sample(samples, f"{text} 样本{round_id}", [label], "balanced_weak_template")
                made_progress = True
                if len(samples) >= target_size:
                    break
            if len(samples) >= target_size:
                break
        round_id += 1
        if not made_progress or round_id > 100:
            break

    ordered = list(samples.values())[:target_size]
    ordered.sort(key=lambda item: (item["labels"][0], item["text"]))
    return ordered


def write_jsonl(samples: list[dict[str, Any]], output_path: str = DEFAULT_OUTPUT) -> Path:
    path = resolve_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(sample, ensure_ascii=False) for sample in samples) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build weak-labeled BERT-mini intent training data.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--target-size", type=int, default=600)
    args = parser.parse_args()
    samples = build_intent_training_samples(target_size=args.target_size)
    path = write_jsonl(samples, args.output)
    counts = Counter(label for sample in samples for label in sample["labels"])
    print(json.dumps({"output": str(path), "count": len(samples), "label_counts": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

