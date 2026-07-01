"""Semi-auto gap computation gold data builder.

For each customer profile, generates template rows with varying employee
answers that cover all/some/none of the expected_intents. The generated
answers are synthetic — human review is needed before the gold set is
reliable. Run this to produce the initial template, then manually verify.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.intent_labels import INTENT_KEYWORDS
from app.utils.file_loader import read_json

PROFILES_PATH = "data/customer_profiles.json"
OUTPUT_PATH = Path("data/eval/gap_computation_gold.jsonl")

ANSWER_TEMPLATES = {
    "rate_concern": [
        "我们这个产品的收益率是比较有竞争力的，您可以看一下利率对比表。",
        "您说得对，利率确实是很重要的考量因素，我帮您查一下目前的最新利率。",
    ],
    "liquidity_concern": [
        "这个产品如果需要提前支取的话，是可以办理的，不过会有一定的利息损失。",
        "关于资金流动性，我建议您可以预留一部分活期资金，这样急用的时候也方便。",
    ],
    "safety_concern": [
        "这个产品的风险是比较低的，但我不能说完全没有风险，具体要看产品说明书。",
        "您的本金安全是有保障的，不过投资都有风险，建议您了解清楚后再做决定。",
    ],
    "procedure_question": [
        "办理这个业务需要您带上身份证到柜台，我帮您预约一个时间怎么样？",
        "流程很简单，您只需要填写一个申请表，我来帮您操作就行。",
    ],
    "rejection_or_hesitation": [
        "没关系的，您回去可以跟家人商量一下，有问题随时联系我。",
        "我理解您需要考虑，不着急，我把资料给您，您看看再说。",
    ],
    "compliance_sensitive": [
        "关于收益我不能给您做任何保证，一切以合同条款和系统显示为准。",
        "我需要提醒您，任何收益演示都不代表对未来收益的承诺。",
    ],
}


def build() -> list[dict[str, Any]]:
    profiles = read_json(PROFILES_PATH, default=[]) or []
    rows: list[dict[str, Any]] = []

    for p in profiles:
        expected = p.get("expected_intents", [])
        if not expected:
            continue
        scene_id = p.get("scene_id", "")
        customer_id = p.get("customer_id", "")

        # Case 1: answer covers ALL expected intents
        full_answer_parts = []
        for intent in expected:
            templates = ANSWER_TEMPLATES.get(intent, [])
            if templates:
                full_answer_parts.append(templates[0])
        if full_answer_parts:
            rows.append({
                "id": f"GG_full_{customer_id}",
                "scene_id": scene_id,
                "customer_id": customer_id,
                "employee_answer": "".join(full_answer_parts),
                "expected_intents": expected,
                "gold_covered": expected,
                "gold_missing": [],
                "coverage_type": "full",
                "needs_review": True,
            })

        # Case 2: answer covers only first intent
        if len(expected) >= 2:
            partial = expected[:1]
            missing = expected[1:]
            templates = ANSWER_TEMPLATES.get(partial[0], [])
            answer = templates[0] if templates else "好的，我来给您介绍一下。"
            rows.append({
                "id": f"GG_partial_{customer_id}",
                "scene_id": scene_id,
                "customer_id": customer_id,
                "employee_answer": answer,
                "expected_intents": expected,
                "gold_covered": partial,
                "gold_missing": missing,
                "coverage_type": "partial",
                "needs_review": True,
            })

        # Case 3: irrelevant answer covering NONE
        rows.append({
            "id": f"GG_none_{customer_id}",
            "scene_id": scene_id,
            "customer_id": customer_id,
            "employee_answer": "您好，欢迎光临，请问您今天需要办什么业务？",
            "expected_intents": expected,
            "gold_covered": [],
            "gold_missing": expected,
            "coverage_type": "none",
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
    full = sum(1 for r in rows if r["coverage_type"] == "full")
    partial = sum(1 for r in rows if r["coverage_type"] == "partial")
    none_ = sum(1 for r in rows if r["coverage_type"] == "none")
    print(f"Generated {count} gap gold rows: {full} full + {partial} partial + {none_} none")
    print(f"Saved to {OUTPUT_PATH}")
    print("NOTE: All rows have needs_review=True — manually verify before using as gold.")


if __name__ == "__main__":
    main()
