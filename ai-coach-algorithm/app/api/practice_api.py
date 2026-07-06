from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.practice_catalog import get_practice_task_detail, list_practice_tasks
from app.core.script_materials import get_script_card, get_task_script_cards


router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/tasks")
def tasks(
    tab: str = "self",
    direction: str | None = None,
    limit: int = 50,
) -> dict[str, object]:
    return list_practice_tasks(tab=tab, direction=direction, limit=limit)


@router.get("/tasks/{task_id}")
def task_detail(task_id: str) -> dict[str, object]:
    task = get_practice_task_detail(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    scripts = get_task_script_cards(task_id)
    cards = (scripts or {}).get("list", [])
    task["scriptEntry"] = {
        "label": "查看标准话术",
        "endpoint": f"/practice/tasks/{task_id}/scripts",
        "count": len(cards),
    }
    task["scriptCards"] = cards
    return task


@router.get("/tasks/{task_id}/scripts")
def task_scripts(task_id: str, limit: int = 6) -> dict[str, object]:
    scripts = get_task_script_cards(task_id, limit=limit)
    if scripts is None:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    return scripts


@router.get("/scripts/{script_id}")
def script_detail(script_id: str, taskId: str | None = None) -> dict[str, object]:
    card = get_script_card(script_id, task_id=taskId)
    if card is None:
        raise HTTPException(status_code=404, detail=f"script not found: {script_id}")
    return card
