from __future__ import annotations

from pydantic import BaseModel


class TutorPromptContextRequest(BaseModel):
    employee_answer: str
    user_id: str | None = None
    scenario_id: str | None = None
    top_k: int = 5

