from __future__ import annotations

from pydantic import BaseModel


class DialogStartRequest(BaseModel):
    user_id: str = "U001"
    scene_id: str = "INS_PERIODIC"
    customer_id: str | None = None
    task_id: str | None = None
    difficulty: str | None = None
    auto_difficulty: bool = True


class DialogReplyRequest(BaseModel):
    session_id: str
    employee_message: str


class DialogFinishRequest(BaseModel):
    session_id: str

