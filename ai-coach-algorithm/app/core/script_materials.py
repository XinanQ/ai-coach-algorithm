from __future__ import annotations

import re
from typing import Any

from app.core.practice_catalog import (
    get_practice_task_detail,
    list_practice_tasks,
    localize_intents,
)
from app.utils.file_loader import read_json


MAX_TASK_SCRIPT_CARDS = 6
MARKETING_CHUNKS_PATH = "data/marketing_chunks.json"

KNOWLEDGE_TYPE_LABELS = {
    "phone_invitation": "客户触达话术",
    "product_intro": "产品讲解话术",
    "objection_handling": "异议处理话术",
    "sales_process": "销售流程话术",
    "compliance_note": "合规风险提示",
    "raw_script": "标准参考话术",
}

DIRECTION_KNOWLEDGE_PRIORITY = {
    "customer_touch": ["phone_invitation", "sales_process", "raw_script"],
    "needs": ["sales_process", "product_intro", "raw_script"],
    "product": ["product_intro", "compliance_note", "sales_process", "raw_script"],
    "objection": ["objection_handling", "product_intro", "compliance_note", "raw_script"],
    "close": ["sales_process", "objection_handling", "product_intro", "raw_script"],
    "compliance": ["compliance_note", "product_intro", "objection_handling", "raw_script"],
    "service": ["sales_process", "raw_script", "product_intro"],
}

INTENT_KEYWORDS = {
    "rate_concern": ["收益", "利率", "分红", "回报", "年化"],
    "liquidity_concern": ["流动", "赎回", "取出", "退保", "期限", "用钱"],
    "safety_concern": ["风险", "本金", "安全", "亏损", "波动"],
    "procedure_question": ["办理", "流程", "材料", "手续", "下一步"],
    "rejection_or_hesitation": ["异议", "拒绝", "考虑", "顾虑", "商量"],
    "compliance_sensitive": ["合规", "承诺", "保本", "保证", "不保证", "合同"],
}

INTENT_CARD_TAGS = {
    "rate_concern": "收益说明",
    "liquidity_concern": "流动性说明",
    "safety_concern": "风险提示",
    "procedure_question": "办理引导",
    "rejection_or_hesitation": "异议处理",
    "compliance_sensitive": "合规表达",
}

KNOWLEDGE_TYPE_TAGS = {
    "phone_invitation": ["客户触达", "邀约话术"],
    "product_intro": ["产品讲解"],
    "objection_handling": ["异议处理", "共情回应"],
    "sales_process": ["流程引导"],
    "compliance_note": ["合规表达", "风险提示"],
    "raw_script": ["参考话术"],
}

GENERIC_TITLES = {"话术", "标准话术", "保险营销话术参考", "参考话术"}


def _load_chunks() -> list[dict[str, Any]]:
    data = read_json(MARKETING_CHUNKS_PATH, default={}) or {}
    chunks = data.get("chunks") if isinstance(data, dict) else []
    return chunks if isinstance(chunks, list) else []


def _business_prefix(scene_id: str | None) -> str:
    return (scene_id or "").split("_", 1)[0]


def _normalize_text(text: str | None) -> str:
    text = (text or "").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _excerpt(text: str, max_chars: int = 90) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "…"


def _display_title(chunk: dict[str, Any], task: dict[str, Any]) -> str:
    title = _normalize_text(str(chunk.get("title") or ""))
    knowledge_type = str(chunk.get("knowledge_type") or "")
    if title and title not in GENERIC_TITLES:
        return title[:28]

    direction_label = task.get("directionLabel") or ""
    knowledge_label = KNOWLEDGE_TYPE_LABELS.get(knowledge_type, "标准话术")
    if direction_label and direction_label not in knowledge_label:
        return f"{direction_label}{knowledge_label}"
    return knowledge_label


def _standard_speech(chunk: dict[str, Any]) -> str:
    text = (
        chunk.get("tutor_view_text")
        or chunk.get("customer_view_text")
        or chunk.get("content")
        or ""
    )
    return _normalize_text(str(text))


def _script_tags(chunk: dict[str, Any], task: dict[str, Any]) -> list[str]:
    knowledge_type = str(chunk.get("knowledge_type") or "")
    tags = list(KNOWLEDGE_TYPE_TAGS.get(knowledge_type, ["标准话术"]))
    text = _standard_speech(chunk)
    for intent in task.get("intentTags") or []:
        if any(keyword in text for keyword in INTENT_KEYWORDS.get(intent, [])):
            tags.append(INTENT_CARD_TAGS.get(intent, intent))
    if chunk.get("compliance_status") == "risk_detected":
        tags.append("需合规复核")
    return list(dict.fromkeys(tag for tag in tags if tag))


def _score_chunk(chunk: dict[str, Any], task: dict[str, Any], allow_risk: bool = False) -> float:
    score = 0.0
    scene_id = str(task.get("sceneId") or "")
    chunk_scene = str(chunk.get("scene_id") or "")
    direction = str(task.get("direction") or "")
    knowledge_type = str(chunk.get("knowledge_type") or "")
    priority = DIRECTION_KNOWLEDGE_PRIORITY.get(direction, ["product_intro", "objection_handling", "raw_script"])

    if chunk_scene == scene_id:
        score += 100
    elif _business_prefix(chunk_scene) == _business_prefix(scene_id):
        score += 42
    else:
        score += 5

    if knowledge_type in priority:
        score += max(0, 35 - priority.index(knowledge_type) * 7)
    else:
        score += 3

    if chunk.get("compliance_status") == "pass":
        score += 20
    elif allow_risk:
        score -= 8
    else:
        score -= 100

    text = _standard_speech(chunk)
    for intent in task.get("intentTags") or []:
        if any(keyword in text for keyword in INTENT_KEYWORDS.get(intent, [])):
            score += 8

    if len(text) < 20:
        score -= 30
    if len(text) > 500:
        score -= 2
    return score


def _build_card(chunk: dict[str, Any], task: dict[str, Any], rank: int) -> dict[str, Any]:
    speech = _standard_speech(chunk)
    chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "")
    knowledge_type = str(chunk.get("knowledge_type") or "")
    scene_name = str(chunk.get("scene_name") or task.get("sceneName") or "")
    knowledge_label = KNOWLEDGE_TYPE_LABELS.get(knowledge_type, "标准话术")
    title = _display_title(chunk, task)
    tags = _script_tags(chunk, task)

    return {
        "scriptId": chunk_id,
        "taskId": task.get("taskId"),
        "sceneId": task.get("sceneId"),
        "sceneName": scene_name,
        "category": chunk.get("business_name") or task.get("category") or "",
        "title": title,
        "subtitle": f"{scene_name} · {knowledge_label}" if scene_name else knowledge_label,
        "knowledgeType": knowledge_type,
        "knowledgeTypeLabel": knowledge_label,
        "tags": tags,
        "standardSpeech": speech,
        "copyText": speech,
        "excerpt": _excerpt(speech),
        "sourceChunkId": chunk_id,
        "sourceSectionId": chunk.get("source_section_id"),
        "sourceFile": chunk.get("source_file"),
        "complianceStatus": chunk.get("compliance_status", "unknown"),
        "rank": rank,
    }


def _ranked_chunks_for_task(task: dict[str, Any], *, allow_risk: bool = False) -> list[dict[str, Any]]:
    chunks = _load_chunks()
    scored = []
    for chunk in chunks:
        speech = _standard_speech(chunk)
        if not speech:
            continue
        score = _score_chunk(chunk, task, allow_risk=allow_risk)
        if score <= 0:
            continue
        scored.append((score, chunk))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored]


def get_task_script_cards(task_id: str, limit: int = MAX_TASK_SCRIPT_CARDS) -> dict[str, Any] | None:
    task = get_practice_task_detail(task_id)
    if task is None:
        return None

    ranked = _ranked_chunks_for_task(task, allow_risk=False)
    if len(ranked) < 2:
        ranked = _ranked_chunks_for_task(task, allow_risk=True)

    cards: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for chunk in ranked:
        speech = _standard_speech(chunk)
        fingerprint = _excerpt(speech, max_chars=80)
        if fingerprint in seen_texts:
            continue
        seen_texts.add(fingerprint)
        cards.append(_build_card(chunk, task, rank=len(cards) + 1))
        if len(cards) >= max(1, int(limit)):
            break

    return {
        "taskId": task.get("taskId"),
        "sceneId": task.get("sceneId"),
        "sceneName": task.get("sceneName"),
        "taskTitle": task.get("title"),
        "total": len(cards),
        "list": cards,
    }


def get_script_card(script_id: str, task_id: str | None = None) -> dict[str, Any] | None:
    if task_id:
        material = get_task_script_cards(task_id, limit=MAX_TASK_SCRIPT_CARDS)
        for card in (material or {}).get("list", []):
            if card.get("scriptId") == script_id:
                return card

    tasks = list_practice_tasks(tab="self", limit=200).get("list", [])
    for task in tasks:
        material = get_task_script_cards(str(task.get("taskId")), limit=MAX_TASK_SCRIPT_CARDS)
        for card in (material or {}).get("list", []):
            if card.get("scriptId") == script_id:
                return card

    # Fallback for a chunk that is not selected by the current task-ranking
    # rules but still exists in the knowledge base.
    for chunk in _load_chunks():
        chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "")
        if chunk_id != script_id:
            continue
        task = {
            "taskId": task_id,
            "sceneId": chunk.get("scene_id"),
            "sceneName": chunk.get("scene_name"),
            "category": chunk.get("business_name"),
            "direction": "",
            "directionLabel": "",
            "intentTags": [],
            "intentLabels": localize_intents([]),
        }
        return _build_card(chunk, task, rank=1)
    return None
