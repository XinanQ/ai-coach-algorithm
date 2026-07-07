from __future__ import annotations

import re
from typing import Any

from app.core.practice_catalog import (
    get_practice_task_detail,
    list_practice_tasks,
    localize_intents,
)
from app.core.script_title_review import (
    get_reviewed_display_title,
    get_reviewed_standard_speech,
    is_script_card_rejected,
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
RAW_TITLE_PREFIX_RE = re.compile(r"^\s*[\(（]?\s*[一二三四五六七八九十百千万\d]+\s*[\)）\.、,:：-]*\s*")

DISPLAY_TITLE_RULES = [
    (("家人", "商量"), "客户想和家人商量时怎么回应"),
    (("考虑", "想想", "犹豫", "回去"), "客户说想再考虑时怎么回应"),
    (("没钱", "没有钱", "闲钱"), "客户说暂时没钱时怎么回应"),
    (("前期没有收益", "返本慢", "回本慢"), "客户质疑前期收益低时怎么解释"),
    (("不知道什么时候要用钱", "中途要用钱", "急着要用钱", "用钱", "取出来", "赎回", "退保", "流动性"), "客户担心未来用钱时怎么回应"),
    (("安全", "靠谱吗", "风险", "本金", "亏损", "波动"), "客户担心资金安全时怎么说明"),
    (("收益并不高", "收益太低", "收益低", "利率低", "分红每年", "通货膨胀", "年化", "回报"), "客户质疑收益时怎么解释"),
    (("保本", "保证", "承诺", "写进合同", "合同"), "客户追问承诺或合同时怎么合规回应"),
    (("费用", "费率", "保费", "缴费", "存不上"), "客户关注费用或缴费压力时怎么回应"),
    (("流程", "手续", "材料", "办理", "怎么购买", "怎么买"), "客户询问办理流程时怎么说明"),
    (("邀约", "到店", "网点", "电话"), "客户邀约到店时怎么开口"),
    (("教育", "养老", "孩子", "补习班"), "客户关注家庭资金安排时怎么回应"),
]
TITLE_FIRST_DISPLAY_RULES = [
    (("前期没有收益", "返本慢", "回本慢"), "客户质疑前期收益低时怎么解释"),
    (("不知道什么时候要用钱", "中途要用钱", "急着要用钱"), "客户担心未来用钱时怎么回应"),
    (("我没钱", "没钱", "没有钱"), "客户说暂时没钱时怎么回应"),
    (("家人", "商量"), "客户想和家人商量时怎么回应"),
    (("考虑", "想想", "犹豫", "回去"), "客户说想再考虑时怎么回应"),
    (("安全", "靠谱吗", "风险"), "客户担心资金安全时怎么说明"),
    (("利率低", "收益低", "收益太低", "分红", "年化"), "客户质疑收益时怎么解释"),
    (("存不上", "缴费", "保费"), "客户关注费用或缴费压力时怎么回应"),
    (("孩子", "补习班", "教育", "养老"), "客户关注家庭资金安排时怎么回应"),
    (("需求分析",), "客户需求分析话术"),
    (("注意事项",), "关键合规注意事项"),
]


def _load_chunks() -> list[dict[str, Any]]:
    data = read_json(MARKETING_CHUNKS_PATH, default={}) or {}
    chunks = data.get("chunks") if isinstance(data, dict) else []
    return chunks if isinstance(chunks, list) else []


def _business_prefix(scene_id: str | None) -> str:
    return (scene_id or "").split("_", 1)[0]


def _scene_relation(chunk_scene: str | None, task_scene: str | None) -> str:
    chunk_scene = chunk_scene or ""
    task_scene = task_scene or ""
    if chunk_scene == task_scene:
        return "exact_scene"
    if _business_prefix(chunk_scene) and _business_prefix(chunk_scene) == _business_prefix(task_scene):
        return "same_business"
    return "cross_business"


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


def _rule_based_display_title(chunk: dict[str, Any], task: dict[str, Any]) -> str:
    title = _normalize_text(str(chunk.get("title") or ""))
    speech = _standard_speech(chunk)
    knowledge_type = str(chunk.get("knowledge_type") or "")
    signal_text = f"{title} {speech[:220]} {task.get('title') or ''} {task.get('description') or ''}"

    for keywords, display_title in TITLE_FIRST_DISPLAY_RULES:
        if any(keyword in title for keyword in keywords):
            return display_title

    for keywords, display_title in DISPLAY_TITLE_RULES:
        if any(keyword in signal_text for keyword in keywords):
            return display_title

    clean_title = RAW_TITLE_PREFIX_RE.sub("", title).strip(" ?？.。:：")
    if clean_title and clean_title not in GENERIC_TITLES and len(clean_title) <= 14:
        return clean_title if clean_title.endswith("话术") else f"{clean_title}话术"

    direction_label = task.get("directionLabel") or ""
    knowledge_label = KNOWLEDGE_TYPE_LABELS.get(knowledge_type, "标准话术")
    if direction_label and direction_label not in knowledge_label:
        return f"{direction_label}{knowledge_label}"

    if clean_title and clean_title not in GENERIC_TITLES:
        return f"{clean_title[:18]}怎么回应"
    return knowledge_label


def _display_title(chunk: dict[str, Any], task: dict[str, Any]) -> str:
    chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "")
    reviewed_title = get_reviewed_display_title(chunk_id)
    if reviewed_title:
        return reviewed_title
    return _rule_based_display_title(chunk, task)


def _standard_speech(chunk: dict[str, Any]) -> str:
    chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "")
    reviewed_speech = get_reviewed_standard_speech(chunk_id)
    if reviewed_speech:
        return _normalize_text(reviewed_speech)

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

    relation = _scene_relation(chunk_scene, scene_id)
    if relation == "exact_scene":
        score += 100
    elif relation == "same_business":
        score += 18
    else:
        score -= 80

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
    display_title = _display_title(chunk, task)
    source_title = _normalize_text(str(chunk.get("title") or ""))
    tags = _script_tags(chunk, task)
    source_scene_id = str(chunk.get("scene_id") or "")

    return {
        "scriptId": chunk_id,
        "taskId": task.get("taskId"),
        "sceneId": task.get("sceneId"),
        "sceneName": scene_name,
        "category": chunk.get("business_name") or task.get("category") or "",
        "title": display_title,
        "displayTitle": display_title,
        "sourceTitle": source_title,
        "subtitle": f"{scene_name} · {knowledge_label}" if scene_name else knowledge_label,
        "knowledgeType": knowledge_type,
        "knowledgeTypeLabel": knowledge_label,
        "tags": tags,
        "standardSpeech": speech,
        "copyText": speech,
        "excerpt": _excerpt(speech),
        "sourceSceneId": source_scene_id,
        "sourceSceneName": scene_name,
        "sourceScope": _scene_relation(source_scene_id, str(task.get("sceneId") or "")),
        "sourceChunkId": chunk_id,
        "sourceSectionId": chunk.get("source_section_id"),
        "sourceFile": chunk.get("source_file"),
        "complianceStatus": chunk.get("compliance_status", "unknown"),
        "rank": rank,
    }


def _ranked_chunks_for_task(
    task: dict[str, Any],
    *,
    allow_risk: bool = False,
    scope: str = "exact_scene",
) -> list[dict[str, Any]]:
    chunks = _load_chunks()
    scored = []
    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "")
        if is_script_card_rejected(chunk_id):
            continue
        speech = _standard_speech(chunk)
        if not speech:
            continue
        relation = _scene_relation(str(chunk.get("scene_id") or ""), str(task.get("sceneId") or ""))
        if scope == "exact_scene" and relation != "exact_scene":
            continue
        if scope == "same_business" and relation != "same_business":
            continue
        if scope == "same_or_exact" and relation not in {"exact_scene", "same_business"}:
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

    requested_limit = max(1, int(limit))
    ranked = _ranked_chunks_for_task(task, allow_risk=False, scope="exact_scene")
    if len(ranked) < requested_limit:
        ranked.extend(_ranked_chunks_for_task(task, allow_risk=False, scope="same_business"))
    if len(ranked) < 2:
        ranked = _ranked_chunks_for_task(task, allow_risk=True, scope="same_or_exact")

    cards: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    for chunk in ranked:
        speech = _standard_speech(chunk)
        fingerprint = _excerpt(speech, max_chars=80)
        if fingerprint in seen_texts:
            continue
        seen_texts.add(fingerprint)
        cards.append(_build_card(chunk, task, rank=len(cards) + 1))
        if len(cards) >= requested_limit:
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
        if is_script_card_rejected(chunk_id):
            return None
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
