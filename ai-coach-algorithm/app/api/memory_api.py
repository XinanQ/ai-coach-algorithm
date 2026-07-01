from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.memory_manager import get_memory_manager
from app.core.weakness_profile import build_weakness_profile
from app.schemas.memory_schema import HistoryRetrieveRequest, SessionUpsertRequest


router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/status")
def status() -> dict[str, object]:
    return get_memory_manager().status()


@router.get("/session/get")
def get_session(session_id: str) -> dict[str, object]:
    session = get_memory_manager().get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return {"session": session}


@router.post("/session/upsert")
def upsert_session(request: SessionUpsertRequest) -> dict[str, object]:
    return {"session": get_memory_manager().upsert_session(request.session)}


@router.get("/longterm/list")
def list_longterm(user_id: str | None = None, scenario_id: str | None = None, limit: int = 20) -> dict[str, object]:
    return {"items": get_memory_manager().list_longterm(user_id=user_id, scenario_id=scenario_id, limit=limit)}


@router.post("/rag-history/retrieve")
def retrieve_history(request: HistoryRetrieveRequest) -> dict[str, object]:
    return {
        "items": get_memory_manager().retrieve_history(
            query=request.query,
            user_id=request.user_id,
            scenario_id=request.scenario_id,
            limit=request.limit,
        )
    }


@router.get("/user-weakness")
def user_weakness(user_id: str, scene_id: str | None = None, limit: int = 10) -> dict[str, object]:
    """返回用户弱点画像：历史弱项、维度趋势、改善建议。"""
    wp = build_weakness_profile(user_id=user_id, scene_id=scene_id, limit=limit)
    return {
        "has_history": wp.has_history(),
        "profile": wp.to_dict(),
        "customer_prompt_preview": wp.to_prompt_text(role="customer"),
        "scorer_prompt_preview": wp.to_prompt_text(role="scorer"),
    }

