"""LLM-driven customer follow-up question generation.

The LLM now returns structured JSON with both the follow-up question AND
intent labels for the employee's answer. This piggybacks intent detection
onto the existing LLM call — zero extra API calls or tokens.

Output format from LLM:
  {"intents": ["rate_concern", ...], "follow_up": "客户追问文本"}

When the LLM is unavailable or fails, returns None and the dialog manager
falls back to the hardcoded CUSTOMER_INTENT_PROBES template.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core.intent_labels import INTENT_LABELS
from app.core.llm.client import is_llm_available
from app.core.llm.parser import clean_plain_text
from app.core.llm.prompts.customer import get_customer_builder_for_scene
from app.core.llm_scorer import _call_llm_text, _call_llm_text_stream

logger = logging.getLogger(__name__)

VALID_INTENTS = set(INTENT_LABELS)


def _parse_customer_response(raw: str | None) -> dict[str, Any] | None:
    """Parse LLM customer response JSON. Returns {"intents": [...], "follow_up": "..."} or None."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match:
            return {"intents": [], "follow_up": clean_plain_text(raw)}
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"intents": [], "follow_up": clean_plain_text(raw)}

    if not isinstance(data, dict):
        return {"intents": [], "follow_up": clean_plain_text(raw)}

    intents = [i for i in data.get("intents", []) if i in VALID_INTENTS]
    follow_up = clean_plain_text(str(data.get("follow_up", "")))
    if not follow_up:
        return None
    return {"intents": intents, "follow_up": follow_up}


def _build_chat_messages(
    profile: dict[str, Any],
    messages: list[dict[str, Any]],
    employee_message: str,
    gap_intents: list[str],
    covered_intents: list[str],
    retrieval_items: list[dict[str, Any]] | None,
    scene_id: str | None,
    weakness_prompt: str,
) -> list[dict[str, str]]:
    if scene_id is None:
        scene_id = profile.get("scene_id")
    builder = get_customer_builder_for_scene(profile, scene_id)
    return builder.to_chat_messages({
        "messages": messages,
        "employee_message": employee_message,
        "gap_intents": gap_intents,
        "covered_intents": covered_intents,
        "retrieval_items": retrieval_items,
        "weakness_prompt": weakness_prompt,
    })


async def generate_customer_question_with_llm(
    profile: dict[str, Any],
    messages: list[dict[str, Any]],
    employee_message: str,
    gap_intents: list[str],
    covered_intents: list[str],
    retrieval_items: list[dict[str, Any]] | None = None,
    scene_id: str | None = None,
    weakness_prompt: str = "",
) -> dict[str, Any] | None:
    """Generate the next customer follow-up via LLM (async).

    Returns {"intents": [...], "follow_up": "..."} or None on failure.
    """
    if not is_llm_available() or not employee_message.strip():
        return None
    if scene_id is None:
        scene_id = profile.get("scene_id")
    chat = _build_chat_messages(
        profile, messages, employee_message,
        gap_intents, covered_intents, retrieval_items, scene_id, weakness_prompt,
    )
    raw = await _call_llm_text(chat, method="customer", scene_id=scene_id)
    return _parse_customer_response(raw)


async def generate_customer_question_stream(
    profile: dict[str, Any],
    messages: list[dict[str, Any]],
    employee_message: str,
    gap_intents: list[str],
    covered_intents: list[str],
    retrieval_items: list[dict[str, Any]] | None = None,
    scene_id: str | None = None,
    weakness_prompt: str = "",
):
    """Async generator that yields customer question text chunks as they stream in.

    Collects the full response, parses JSON at the end, and yields a final
    metadata event with the detected intents.
    """
    if not is_llm_available() or not employee_message.strip():
        return
    if scene_id is None:
        scene_id = profile.get("scene_id")
    chat = _build_chat_messages(
        profile, messages, employee_message,
        gap_intents, covered_intents, retrieval_items, scene_id, weakness_prompt,
    )
    async for chunk in _call_llm_text_stream(chat, method="customer", scene_id=scene_id):
        yield chunk
