"""联调 JSON contract.


"""
from __future__ import annotations

import uuid
from typing import Any


SOURCE_RULE_BASED = "RULE_BASED"
SOURCE_LLM_BASED = "LLM_BASED"


def _source_from_method(method: str | None) -> str:
    """Map scorer method -> 联调 source enum."""
    if method and method.startswith("llm_scorer"):
        return SOURCE_LLM_BASED
    return SOURCE_RULE_BASED


def _level(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 75:
        return "良好"
    if score >= 60:
        return "合格"
    return "待提升"


def _certification(dimension_scores: list[dict[str, Any]], total: int) -> dict[str, str]:
    """First-stage rule-based certification title from the strongest dimension."""
    if total < 60 or not dimension_scores:
        return {"title": "", "desc": ""}
    best = max(dimension_scores, key=lambda d: d.get("score", 0))
    title_map = {
        "合规度": "合规揭示达人",
        "异议处理": "异议处理能手",
        "逻辑结构": "结构表达达人",
        "共情力": "客户共情达人",
    }
    title = title_map.get(best.get("name", ""), "陪练进阶达人")
    return {"title": f"新晋「{title}」", "desc": f"{best.get('name', '')}表现突出，完成专项认证"}


def present_start(result: dict[str, Any]) -> dict[str, Any]:
    """Map start_dialogue() output to the 联调 start response."""
    session = result.get("session", {})
    opening = result.get("ai_customer_message", "")
    resp: dict[str, Any] = {
        "sessionId": session.get("session_id"),
        "taskId": session.get("task_id") or session.get("scene_id"),
        "round": int(session.get("round", 1)),
        "totalRounds": int(session.get("total_rounds", 3)),
        "difficultyLevel": session.get("difficulty_level", "中"),
        "messages": [{"role": "ai", "content": opening}] if opening else [],
    }
    if result.get("difficulty_recommendation"):
        resp["difficultyRecommendation"] = result["difficulty_recommendation"]
    return resp


def present_reply(result: dict[str, Any]) -> dict[str, Any]:
    """Map reply_dialogue() output to the 联调 reply response.

    Per-turn live scoring was removed, so the reply no longer carries a
    liveScore / source — the score is delivered once by /dialog/finish.
    """
    next_text = result.get("ai_customer_message")
    return {
        "round": int(result.get("round", 1)),
        "totalRounds": int(result.get("total_rounds", 3)),
        "message": {"role": "ai", "content": next_text} if next_text else None,
        "finished": bool(result.get("finished", False)),
    }


def present_finish(result: dict[str, Any]) -> dict[str, Any]:
    """Map finish_dialogue() output to the 联调 finish response.

    Algorithm fields (score / dimensionScores / weakTags / suggestion) are real.
    Business fields (resultId / taskId / scoreDelta / rewards / certification)
    are first-stage mock values — wire them to the real backend later.
    """
    session = result.get("session", {})
    longterm = result.get("longterm_memory", {})
    score_result = session.get("score_result") or longterm.get("score_result") or {}

    total = int(score_result.get("total_score", 0))
    dimension_scores = score_result.get("dimension_scores", [])
    dimensions = [
        {"name": dim.get("name", dim.get("key", "")), "score": int(dim.get("score", 0)), "level": _level(int(dim.get("score", 0)))}
        for dim in dimension_scores
    ]
    cert = _certification(dimensions, total)

    # taskId: we key dialogues by scene; until the backend maps taskId->scene,
    # surface the scene id as the task id so the front-end has a stable handle.
    task_id = session.get("task_id") or session.get("scene_id") or session.get("scenario_id")

    return {
        "resultId": longterm.get("memory_id") or f"r_{uuid.uuid4().hex[:10]}",
        "taskId": task_id,
        "score": total,
        # --- business fields below are first-stage mock; backend owns them ---
        "scoreDelta": 0,
        "certificationTitle": cert["title"],
        "certificationDesc": cert["desc"],
        "rewardPoints": max(10, total),
        "rewardExp": max(10, total) * 2,
        # --- algorithm fields ---
        "dimensionScores": dimensions,
        "weakTags": score_result.get("weakness_tags", []),
        "suggestion": score_result.get("suggestion", ""),
        "source": _source_from_method(score_result.get("method")),
    }
