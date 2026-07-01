from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dialog_presenter import present_finish, present_reply, present_start
from app.core.adaptive_difficulty import recommend_difficulty
from app.core.dialog_manager import finish_dialogue, list_profiles, reply_dialogue, reply_dialogue_stream, start_dialogue
from app.schemas.dialog_schema import DialogFinishRequest, DialogReplyRequest, DialogStartRequest


router = APIRouter(prefix="/dialog", tags=["dialog"])


@router.get("/profiles")
def profiles() -> dict[str, object]:
    return {"profiles": list_profiles()}


@router.post("/start")
def start(request: DialogStartRequest) -> dict[str, object]:
    result = start_dialogue(
        user_id=request.user_id,
        scene_id=request.scene_id,
        customer_id=request.customer_id,
        task_id=request.task_id,
        total_rounds=request.total_rounds,
        difficulty=request.difficulty,
        auto_difficulty=request.auto_difficulty,
    )
    return present_start(result)


@router.get("/difficulty-recommendation")
def difficulty_recommendation(
    user_id: str, scene_id: str, current_difficulty: str = "中",
) -> dict[str, object]:
    rec = recommend_difficulty(
        user_id=user_id, scene_id=scene_id, current_difficulty=current_difficulty,
    )
    return rec.to_dict()


@router.post("/reply")
async def reply(request: DialogReplyRequest) -> dict[str, object]:
    try:
        result = await reply_dialogue(
            session_id=request.session_id, employee_message=request.employee_message
        )
        return present_reply(result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reply/stream")
async def reply_stream(request: DialogReplyRequest):
    """SSE endpoint that streams the AI customer's follow-up question token by token.

    Event types:
      - meta:     intent/gap analysis result (sent immediately)
      - delta:    one text chunk from the LLM stream
      - done:     final assembled message after stream completes
      - fallback: full message from template fallback (no streaming)
      - error:    error message
    """
    async def event_generator():
        try:
            async for event in reply_dialogue_stream(
                session_id=request.session_id, employee_message=request.employee_message
            ):
                event_type = event["event"]
                data = json.dumps(event["data"], ensure_ascii=False) if not isinstance(event["data"], str) else event["data"]
                yield f"event: {event_type}\ndata: {data}\n\n"
        except KeyError as exc:
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/finish")
async def finish(request: DialogFinishRequest) -> dict[str, object]:
    try:
        result = await finish_dialogue(session_id=request.session_id)
        # Adapt to the mini-program 联调 contract (camelCase + business fields).
        return present_finish(result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

