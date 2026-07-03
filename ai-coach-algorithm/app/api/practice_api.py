from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.practice_catalog import get_practice_task_detail, list_practice_tasks


router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/tasks")
def tasks(tab: str = "self", direction: str | None = "objection", limit: int = 20) -> dict[str, object]:
    return list_practice_tasks(tab=tab, direction=direction, limit=limit)


@router.get("/tasks/{task_id}")
def task_detail(task_id: str) -> dict[str, object]:
    task = get_practice_task_detail(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    return task
