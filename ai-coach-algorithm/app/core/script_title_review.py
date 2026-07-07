from __future__ import annotations

from pathlib import Path
from typing import Any

from app.utils.file_loader import read_json, resolve_path


SCRIPT_TITLE_OVERRIDES_PATH = "data/script_title_overrides.json"
APPROVED_STATUSES = {"approved", "locked"}
REJECTED_STATUSES = {"rejected"}

_CACHE_PATH: Path | None = None
_CACHE_MTIME: float | None = None
_CACHE_DATA: dict[str, dict[str, Any]] | None = None


def load_script_title_overrides() -> dict[str, dict[str, Any]]:
    global _CACHE_DATA, _CACHE_MTIME, _CACHE_PATH
    file_path = resolve_path(SCRIPT_TITLE_OVERRIDES_PATH)
    mtime = file_path.stat().st_mtime if file_path.exists() else None
    if _CACHE_DATA is not None and _CACHE_PATH == file_path and _CACHE_MTIME == mtime:
        return _CACHE_DATA

    data = read_json(SCRIPT_TITLE_OVERRIDES_PATH, default={}) or {}
    overrides = data.get("overrides") if isinstance(data, dict) else {}
    if not isinstance(overrides, dict):
        _CACHE_PATH = file_path
        _CACHE_MTIME = mtime
        _CACHE_DATA = {}
        return _CACHE_DATA

    normalized: dict[str, dict[str, Any]] = {}
    for chunk_id, item in overrides.items():
        if not isinstance(item, dict):
            continue
        normalized[str(chunk_id)] = item
    _CACHE_PATH = file_path
    _CACHE_MTIME = mtime
    _CACHE_DATA = normalized
    return _CACHE_DATA


def clear_script_title_override_cache() -> None:
    global _CACHE_DATA, _CACHE_MTIME, _CACHE_PATH
    _CACHE_PATH = None
    _CACHE_MTIME = None
    _CACHE_DATA = None


def get_reviewed_display_title(chunk_id: str | None) -> str | None:
    if not chunk_id:
        return None
    item = load_script_title_overrides().get(str(chunk_id))
    if not item:
        return None
    if str(item.get("status") or "").lower() not in APPROVED_STATUSES:
        return None
    title = str(item.get("displayTitle") or "").strip()
    return title or None


def get_reviewed_standard_speech(chunk_id: str | None) -> str | None:
    if not chunk_id:
        return None
    item = load_script_title_overrides().get(str(chunk_id))
    if not item:
        return None
    if str(item.get("status") or "").lower() not in APPROVED_STATUSES:
        return None
    speech = str(item.get("standardSpeech") or "").strip()
    return speech or None


def is_script_card_rejected(chunk_id: str | None) -> bool:
    if not chunk_id:
        return False
    item = load_script_title_overrides().get(str(chunk_id))
    if not item:
        return False
    return str(item.get("status") or "").lower() in REJECTED_STATUSES
