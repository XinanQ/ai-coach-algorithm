from __future__ import annotations

from typing import Any

from app.core.customer_profile_loader import load_customer_profiles
from app.core.dialog_round_policy import build_dialog_round_policy


INTENT_LABELS = {
    "rate_concern": "收益关注",
    "liquidity_concern": "流动性担忧",
    "safety_concern": "本金安全",
    "procedure_question": "办理流程",
    "rejection_or_hesitation": "拒绝犹豫",
    "compliance_sensitive": "合规敏感",
}

TAB_DEFS = [
    {"key": "assigned", "label": "上级下发"},
    {"key": "self", "label": "自主任务"},
    {"key": "done", "label": "已完成"},
]

DIRECTION_DEFS = [
    {"key": "customer_touch", "label": "客户触达"},
    {"key": "needs", "label": "需求识别"},
    {"key": "product", "label": "产品讲解"},
    {"key": "objection", "label": "异议处理"},
    {"key": "close", "label": "成交促成"},
    {"key": "compliance", "label": "合规风险"},
    {"key": "service", "label": "售后维护"},
]

DIRECTION_ALIASES = {
    item["key"]: item["key"] for item in DIRECTION_DEFS
} | {
    item["label"]: item["key"] for item in DIRECTION_DEFS
}

CATEGORY_BY_PREFIX = {
    "INS": "保险",
    "FUND": "基金",
    "WM": "理财",
    "CC": "信用卡",
    "DEP": "存款",
}

DIFFICULTY_TAGS = {
    "低": "低难度",
    "中": "中等",
    "高": "高难度",
}

DEFAULT_GROWTH = {
    "levelName": "Lv5 专业进阶",
    "points": 1260,
    "target": 1800,
    "streakDays": 7,
    "weekGain": 320,
}

SCENE_DIRECTION_OVERRIDES = {
    "INS_PERIODIC": "product",
    "INS_DIVIDEND": "objection",
    "INS_GENERAL": "close",
    "FUND_GENERAL": "close",
    "FUND_FIXED_INVEST": "product",
    "FUND_SALE": "product",
    "FUND_INVITE": "customer_touch",
    "INS_INVITE": "customer_touch",
    "FUND_OBJECTION": "objection",
    "INS_OBJECTION": "objection",
    "INS_PROCESS": "product",
    "WM_ASSET": "needs",
    "WM_GENERAL": "service",
    "WM_PRODUCT": "product",
}


def localize_intents(intent_tags: list[str] | None) -> list[str]:
    return [INTENT_LABELS.get(tag, tag) for tag in intent_tags or []]


def normalize_direction(direction: str | None) -> str | None:
    if not direction:
        return None
    return DIRECTION_ALIASES.get(direction, direction)


def _direction_label(direction_key: str | None) -> str:
    for item in DIRECTION_DEFS:
        if item["key"] == direction_key:
            return item["label"]
    return direction_key or "产品讲解"


def _category_for_scene(scene_id: str | None) -> str:
    prefix = (scene_id or "").split("_", 1)[0]
    return CATEGORY_BY_PREFIX.get(prefix, "综合")


def _duration_for_difficulty(difficulty: str | None) -> int:
    if difficulty == "高":
        return 8
    if difficulty == "低":
        return 6
    return 7


def _default_direction(profile: dict[str, Any]) -> str:
    scene_id = str(profile.get("scene_id") or "")
    difficulty = str(profile.get("difficulty_level") or "")
    scene_name = str(profile.get("scene_name") or "")
    intents = set(profile.get("expected_intents") or [])
    if scene_id.endswith("_INVITE"):
        return "customer_touch"
    if "compliance_sensitive" in intents and difficulty in {"高", "high", "HIGH"}:
        return "compliance"
    if scene_id in SCENE_DIRECTION_OVERRIDES:
        return SCENE_DIRECTION_OVERRIDES[scene_id]
    if "邀约" in scene_name:
        return "customer_touch"
    if "资产配置" in scene_name or "综合" in scene_name:
        return "needs"
    if "流程" in scene_name or "产品" in scene_name or "销售关键点" in scene_name:
        return "product"
    if "rejection_or_hesitation" in intents or "异议" in scene_name:
        return "objection"
    if "compliance_sensitive" in intents:
        return "compliance"
    return "product"


def _profile_by_customer_id() -> dict[str, dict[str, Any]]:
    return {str(p.get("customer_id")): p for p in load_customer_profiles() if p.get("customer_id")}


def _profile_for_task(task: dict[str, Any], profiles: dict[str, dict[str, Any]]) -> dict[str, Any]:
    customer_id = task.get("customer_id")
    if customer_id and customer_id in profiles:
        return profiles[customer_id]
    scene_id = task.get("scene_id") or task.get("scenario_id")
    difficulty = task.get("difficulty_level")
    for profile in profiles.values():
        if profile.get("scene_id") == scene_id and (not difficulty or profile.get("difficulty_level") == difficulty):
            return profile
    return {}


def _build_profile_task(profile: dict[str, Any]) -> dict[str, Any]:
    scene_id = profile.get("scene_id")
    difficulty = profile.get("difficulty_level")
    return {
        "task_id": f"TASK_{profile.get('customer_id')}",
        "scene_id": scene_id,
        "customer_id": profile.get("customer_id"),
        "title": f"{profile.get('scene_name')} · {profile.get('customer_type')}",
        "tab": "self",
        "level": "recommend",
        "status": "active",
        "direction": _default_direction(profile),
        "duration_minutes": _duration_for_difficulty(difficulty),
        "difficulty_level": difficulty,
        "description": profile.get("concern", ""),
        "intent_tags": profile.get("expected_intents", []),
    }


def _profile_tasks() -> list[dict[str, Any]]:
    return [_build_profile_task(profile) for profile in load_customer_profiles()]


def _raw_tasks() -> list[dict[str, Any]]:
    return _profile_tasks()


def _present_task(task: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = profile or {}
    scene_id = task.get("scene_id") or task.get("scenario_id") or profile.get("scene_id")
    difficulty = task.get("difficulty_level") or profile.get("difficulty_level") or "中"
    direction_key = normalize_direction(task.get("direction")) or _default_direction(profile)
    intent_tags = task.get("intent_tags") or task.get("expected_intents") or profile.get("expected_intents") or []
    raw_tags = task.get("tags") or localize_intents(intent_tags)
    tags = [raw_tags] if isinstance(raw_tags, str) else list(raw_tags)
    if difficulty and not any(tag in DIFFICULTY_TAGS.values() for tag in tags):
        tags = list(tags) + [DIFFICULTY_TAGS.get(difficulty, difficulty)]
    duration_minutes = int(task.get("duration_minutes") or _duration_for_difficulty(difficulty))
    round_policy = build_dialog_round_policy(
        direction=direction_key,
        difficulty=difficulty,
        expected_intents=intent_tags,
        scene_id=scene_id,
    )
    return {
        "taskId": task.get("task_id") or task.get("taskId"),
        "sceneId": scene_id,
        "sceneName": task.get("scene_name") or profile.get("scene_name") or "",
        "customerId": task.get("customer_id") or profile.get("customer_id"),
        "customerType": task.get("customer_type") or profile.get("customer_type") or "",
        "title": task.get("title") or f"{profile.get('scene_name', '训练场景')} · {profile.get('customer_type', '')}".strip(" ·"),
        "category": task.get("category") or _category_for_scene(scene_id),
        "direction": direction_key,
        "directionLabel": _direction_label(direction_key),
        "tab": task.get("tab", "self"),
        "level": task.get("level", "recommend"),
        "status": task.get("status", "active"),
        "priorityLabel": task.get("priority_label", "推荐"),
        "durationMinutes": duration_minutes,
        "durationText": f"{duration_minutes}分钟",
        "difficultyLevel": difficulty,
        "tags": tags,
        "intentTags": intent_tags,
        "intentLabels": localize_intents(intent_tags),
        "description": task.get("description") or profile.get("concern") or "",
        "recommendedReason": task.get("recommended_reason", ""),
        "minRounds": round_policy.min_rounds,
        "targetRounds": round_policy.target_rounds,
        "maxRounds": round_policy.max_rounds,
        "totalRounds": round_policy.max_rounds,
        "roundPolicy": round_policy.to_dict(),
    }


def list_practice_tasks(
    tab: str = "self",
    direction: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    profiles = _profile_by_customer_id()
    selected_direction = normalize_direction(direction)
    items: list[dict[str, Any]] = []
    for raw_task in _raw_tasks():
        profile = _profile_for_task(raw_task, profiles)
        task = _present_task(raw_task, profile)
        if tab and tab != "all" and task.get("tab") != tab:
            continue
        if selected_direction and task.get("direction") != selected_direction:
            continue
        items.append(task)

    returned = items[: max(1, int(limit))]
    return {
        **DEFAULT_GROWTH,
        "tabs": TAB_DEFS,
        "directions": DIRECTION_DEFS,
        "selectedTab": tab,
        "selectedDirection": selected_direction,
        "total": len(items),
        "returned": len(returned),
        "list": returned,
    }


def get_practice_task_detail(task_id: str) -> dict[str, Any] | None:
    profiles = _profile_by_customer_id()
    for raw_task in _raw_tasks():
        if raw_task.get("task_id") != task_id and raw_task.get("taskId") != task_id:
            continue
        profile = _profile_for_task(raw_task, profiles)
        task = _present_task(raw_task, profile)
        return {
            **task,
            "customerDesc": raw_task.get("customer_desc") or profile.get("personality") or "",
            "background": raw_task.get("background") or profile.get("concern") or "",
            "openingQuestion": profile.get("opening_question", ""),
            "goal": raw_task.get("goal") or f"完成 {task['minRounds']}-{task['maxRounds']} 轮对话，覆盖客户核心顾虑并保持合规表达。",
            "requirements": raw_task.get("requirements") or ["完成规定轮次", "覆盖客户核心顾虑", "避免绝对化承诺"],
        }
    return None


def with_profile_display_fields(profile: dict[str, Any]) -> dict[str, Any]:
    copied = dict(profile)
    scene_id = copied.get("scene_id")
    difficulty = copied.get("difficulty_level")
    intent_tags = copied.get("expected_intents") or []
    direction_key = _default_direction(copied)
    duration_minutes = _duration_for_difficulty(difficulty)
    copied.update(
        {
            "sceneId": scene_id,
            "sceneName": copied.get("scene_name"),
            "customerId": copied.get("customer_id"),
            "customerType": copied.get("customer_type"),
            "difficultyLevel": difficulty,
            "category": _category_for_scene(scene_id),
            "direction": direction_key,
            "directionLabel": _direction_label(direction_key),
            "durationMinutes": duration_minutes,
            "durationText": f"{duration_minutes}分钟",
            "title": f"{copied.get('scene_name')} · {copied.get('customer_type')} · {difficulty}",
            "tags": localize_intents(intent_tags),
            "expectedIntents": intent_tags,
            "intentLabels": localize_intents(intent_tags),
        }
    )
    return copied
