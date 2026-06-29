from __future__ import annotations

from typing import Any

from app.utils.file_loader import read_json


def load_customer_profiles() -> list[dict[str, Any]]:
    data = read_json("data/customer_profiles.json", default=[]) or []
    return data if isinstance(data, list) else []


def get_customer_profile(
    scene_id: str | None = None,
    customer_id: str | None = None,
    difficulty: str | None = None,
) -> dict[str, Any]:
    profiles = load_customer_profiles()
    if customer_id:
        for profile in profiles:
            if profile.get("customer_id") == customer_id:
                return profile
    if scene_id:
        scene_profiles = [p for p in profiles if p.get("scene_id") == scene_id]
        if difficulty and scene_profiles:
            for p in scene_profiles:
                if p.get("difficulty_level") == difficulty:
                    return p
        if scene_profiles:
            return scene_profiles[0]
    return profiles[0] if profiles else {}


def list_profiles_by_scene(scene_id: str) -> list[dict[str, Any]]:
    return [p for p in load_customer_profiles() if p.get("scene_id") == scene_id]
