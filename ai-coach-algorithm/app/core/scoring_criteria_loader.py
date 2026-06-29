from __future__ import annotations

from typing import Any

from app.utils.file_loader import read_json


CRITERIA_PATH = "data/marketing_scoring_criteria.json"

# When a scene has several criteria (one per knowledge_type), prefer the most
# interactive / objection-driven rubric for tutor scoring of a练习 dialogue.
KNOWLEDGE_TYPE_PRIORITY = [
    "objection_handling",
    "product_intro",
    "sales_process",
    "raw_script",
    "phone_invitation",
    "compliance_note",
]


def load_scoring_criteria() -> list[dict[str, Any]]:
    data = read_json(CRITERIA_PATH, default={}) or {}
    if isinstance(data, dict):
        criteria = data.get("criteria", [])
    else:
        criteria = data
    return [c for c in criteria if isinstance(c, dict) and c.get("enabled", True) is not False]


def get_criteria_for_scene(scene_id: str | None) -> list[dict[str, Any]]:
    if not scene_id:
        return []
    return [c for c in load_scoring_criteria() if c.get("scene_id") == scene_id]


def get_primary_criterion(
    scene_id: str | None,
    knowledge_type: str | None = None,
) -> dict[str, Any]:
    """Direct lookup of the rubric that applies to a scene.

    The scene fully determines which criterion applies, so we look it up by
    scene_id (and optional knowledge_type) instead of semantic search over the
    criteria — that would risk pulling a different scene's rubric.
    """
    candidates = get_criteria_for_scene(scene_id)
    if not candidates:
        return {}
    if knowledge_type:
        for criterion in candidates:
            if criterion.get("knowledge_type") == knowledge_type:
                return criterion
    priority = {kt: idx for idx, kt in enumerate(KNOWLEDGE_TYPE_PRIORITY)}
    candidates.sort(key=lambda c: priority.get(c.get("knowledge_type"), len(priority)))
    return candidates[0]
