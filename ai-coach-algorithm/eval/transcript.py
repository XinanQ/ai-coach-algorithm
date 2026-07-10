"""Stable transcript fingerprints used to bind reviewed bands to exact text."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def transcript_hash(scene_id: str | None, dialog_pairs: list[dict[str, Any]]) -> str:
    payload = {
        "scene_id": scene_id or "",
        "dialog_pairs": [
            {
                "customer_question": str(pair.get("customer_question") or "").strip(),
                "employee_answer": str(pair.get("employee_answer") or "").strip(),
            }
            for pair in dialog_pairs
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
