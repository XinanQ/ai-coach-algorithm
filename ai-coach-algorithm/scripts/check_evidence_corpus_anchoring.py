"""Offline sanity check: is every gold evidence category matchable in its scene corpus?

For each (scene_id, evidence_category) used by e2e_dialog_gold.jsonl, count how
many corpus chunks of that scene contain at least one CORE synonym of the
category (the same synonym map the e2e retrieval checker uses). A count of 0
means no retrieval result could ever satisfy the checker for that turn — a
definite ruler error (gold evidence term detached from corpus wording), fully
decidable offline without running the eval.

Usage:
    python scripts/check_evidence_corpus_anchoring.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

GOLD = Path("data/eval/e2e_dialog_gold.jsonl")
INDEX = Path("data/marketing_vector_index.json")

# Keep in sync with eval/stages/_eval_e2e_impl.py::_validate_retrieval
SYNONYM_MAP = {
    "合规": ["合规", "监管", "规定", "规范", "边界", "红线", "不能承诺", "不承诺", "不保本", "不保息",
            "不实承诺", "夸大", "诱导", "保监会", "双录"],
    "风险": ["风险", "亏损", "波动", "不确定", "本金", "市场", "损失"],
    "流动性": ["流动性", "退保", "现金价值", "犹豫期", "可取", "支取", "赎回", "用钱", "交不上", "续存"],
    "费用": ["费用", "缴费", "保费", "费率", "交费"],
    "收益": ["收益", "回报", "分红", "利率", "利息"],
    "共情": ["共情", "理解", "顾虑", "担心", "认可", "尊重"],
    "理解": ["理解", "明白", "认可", "认同", "顾虑"],
    "需求": ["需求", "风险承受", "期限", "偏好", "确认", "了解"],
    "办理": ["办理", "流程", "手续", "材料", "操作", "下一步"],
    "引导": ["引导", "建议", "指导", "方案", "邀约"],
    "异议": ["异议", "拒绝", "犹豫", "顾虑", "担心", "担忧", "商量", "解决方案", "方案", "灵活", "考虑"],
    "产品": ["产品", "保障", "功能", "条款", "介绍"],
    "适当性": ["适当性", "风险测评", "风险等级", "风险偏好", "承受能力", "匹配"],
    "合同": ["合同", "条款", "说明书", "约定", "责任"],
    "保障": ["保障", "保障责任", "责任", "条款", "保险责任"],
    "清晰说明": ["通俗", "清晰", "重点", "简明", "解释"],
}


def _chunks_by_scene() -> dict[str, list[str]]:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    chunks = data.get("chunks") or data.get("items") or data
    by_scene: dict[str, list[str]] = defaultdict(list)
    if isinstance(chunks, dict):
        chunks = list(chunks.values())
    for ch in chunks:
        if not isinstance(ch, dict):
            continue
        meta = ch.get("metadata") or ch
        scene = meta.get("scene_id")
        text = (ch.get("content") or "") + " " + (meta.get("title") or "")
        if scene:
            by_scene[scene].append(text)
    return by_scene


def main() -> None:
    by_scene = _chunks_by_scene()
    print(f"corpus scenes: { {s: len(c) for s, c in sorted(by_scene.items())} }")

    # Collect (scene, category, case_id, turn) usages from gold.
    usages: dict[tuple[str, str], list[str]] = defaultdict(list)
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        scene = case.get("scene_id")
        for idx, evid in enumerate(case.get("expected_customer_evidence_after_each_turn") or []):
            for cat in evid or []:
                usages[(scene, cat)].append(f"{case.get('id')}#t{idx}")

    print(f"\n{'scene':<16} {'category':<8} {'chunks-with-core-hit':<22} usage")
    dead = []
    for (scene, cat), where in sorted(usages.items()):
        syns = SYNONYM_MAP.get(cat, [cat])
        texts = by_scene.get(scene, [])
        hit_chunks = sum(1 for t in texts if any(s in t for s in syns))
        marker = "  <-- DEAD (can never pass)" if hit_chunks == 0 else ""
        print(f"{scene:<16} {cat:<8} {hit_chunks}/{len(texts):<20} {len(where)} turns{marker}")
        if hit_chunks == 0:
            dead.append((scene, cat, where))

    if dead:
        print("\nDEAD combinations (definite ruler errors):")
        for scene, cat, where in dead:
            print(f"  {scene} × {cat}: {where}")
    else:
        print("\nNo dead combinations — remaining failures depend on which top-5 was returned (audit needed).")


if __name__ == "__main__":
    main()
