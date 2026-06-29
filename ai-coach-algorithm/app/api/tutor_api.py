from __future__ import annotations

from fastapi import APIRouter

from app.core.marketing_tutor_context import build_tutor_prompt_context
from app.schemas.tutor_schema import TutorPromptContextRequest


router = APIRouter(prefix="/marketing-tutor", tags=["marketing-tutor"])


@router.post("/prompt-context")
def prompt_context(request: TutorPromptContextRequest) -> dict[str, object]:
    return build_tutor_prompt_context(
        employee_answer=request.employee_answer,
        user_id=request.user_id,
        scenario_id=request.scenario_id,
        top_k=request.top_k,
    )

