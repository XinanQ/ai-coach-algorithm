"""LLM-driven customer follow-up question generation.

The original design: LLM simulates the customer; the algorithm's job is to
identify employee answer intent and *assist* the LLM in generating the next
follow-up question. This module is that LLM assist — a thin wrapper that
composes the 5-layer customer prompt + invokes the async client + cleans the
output.

Inputs (provided by the algorithm):
  - customer profile (personality / concern / difficulty / type)
  - conversation history
  - employee's latest message
  - gap_intents (concerns NOT yet addressed by the employee)
  - covered_intents (concerns already addressed)
  - retrieval items (relevant standard customer scripts to ground tone in)

Output: a single natural in-character customer utterance. When the LLM is
unavailable or fails, returns None and the dialog manager falls back to the
hardcoded CUSTOMER_INTENT_PROBES template.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.llm.client import is_llm_available
from app.core.llm.parser import clean_plain_text
from app.core.llm.prompts.customer import get_customer_builder_for_scene
from app.core.llm_scorer import _call_llm_text

logger = logging.getLogger(__name__)

# Builder is now per-scene — each scene_id gets its own cached builder whose
# SceneAnchorLayer has the profile baked in as a static layer. Same-scene
# calls share the same prefix bytes → DeepSeek prompt cache hits.


async def generate_customer_question_with_llm(
    profile: dict[str, Any],
    messages: list[dict[str, Any]],
    employee_message: str,
    gap_intents: list[str],
    covered_intents: list[str],
    retrieval_items: list[dict[str, Any]] | None = None,
    scene_id: str | None = None,
    weakness_prompt: str = "",
) -> str | None:
    """Generate the next customer follow-up via LLM (async). None on failure."""
    if not is_llm_available() or not employee_message.strip():
        return None
    if scene_id is None:
        scene_id = profile.get("scene_id")
    builder = get_customer_builder_for_scene(profile, scene_id)
    chat = builder.to_chat_messages({
        "messages": messages,
        "employee_message": employee_message,
        "gap_intents": gap_intents,
        "covered_intents": covered_intents,
        "retrieval_items": retrieval_items,
        "weakness_prompt": weakness_prompt,
    })
    text = await _call_llm_text(chat, method="customer", scene_id=scene_id)
    return clean_plain_text(text)
