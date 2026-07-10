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

import logging
import os
import threading
import time
from typing import Any

from app.core.intent_labels import INTENT_LABELS
from app.core.llm.client import is_llm_available
from app.core.llm.parser import clean_plain_text, parse_json_lenient
from app.core.llm.prompts.customer import get_customer_builder_for_scene
from app.core.llm_scorer import _call_llm_text, _call_llm_text_stream

logger = logging.getLogger(__name__)

VALID_INTENTS = set(INTENT_LABELS)

# ---------------------------------------------------------------------------
# Prefix-cache warmup
#
# The first LLM call for a customer profile pays full-price prefill on its
# ~2k-token static prefix (persona + boundaries + format + scene anchor).
# /dialog/start gives us a natural idle window — the user is reading the
# opening question — so we fire a max_tokens=1 request with the same static
# prefix in a daemon thread. By the time round 1 arrives, DeepSeek's prefix
# cache is hot and the reply's TTFT drops accordingly.
# Disable with AI_COACH_PREFIX_WARMUP=0.
# ---------------------------------------------------------------------------
_PREFIX_WARMUP_ENABLED = os.getenv("AI_COACH_PREFIX_WARMUP", "1").lower() not in ("0", "false", "off")
_WARM_TTL_SECONDS = 600.0
_warmed_at: dict[str, float] = {}


def warm_customer_prefix(profile: dict[str, Any] | None, scene_id: str | None) -> None:
    """Fire-and-forget prefix-cache warmup for one customer profile.

    Never raises and never blocks the caller; all failures are debug-logged.
    Deduped per profile within a TTL so repeated /dialog/start calls in the
    same scene don't spend extra tokens.
    """
    if not _PREFIX_WARMUP_ENABLED or not is_llm_available():
        return
    key = f"{scene_id or 'default'}::{(profile or {}).get('customer_id') or 'default'}"
    now = time.time()
    if now - _warmed_at.get(key, 0.0) < _WARM_TTL_SECONDS:
        return
    _warmed_at[key] = now

    def _run() -> None:
        try:
            from app.core.llm.client import DEFAULT_MODEL, get_sync_client

            client = get_sync_client()
            if client is None:
                return
            builder = get_customer_builder_for_scene(profile, scene_id)
            # Empty dynamic context: the rendered static layers (and therefore
            # the cacheable byte prefix) are identical to real reply calls.
            messages = builder.to_chat_messages({
                "messages": [],
                "employee_message": "",
                "gap_intents": [],
                "covered_intents": [],
                "retrieval_items": [],
                "weakness_prompt": "",
            })
            client.chat.completions.create(
                model=DEFAULT_MODEL, messages=messages, max_tokens=1, temperature=0.0,
            )
            logger.debug("prefix warmup done for %s", key)
        except Exception:
            # Warmup is best-effort; a failure only means the first real call
            # pays the cache miss it would have paid anyway.
            logger.debug("prefix warmup failed for %s", key, exc_info=True)

    threading.Thread(target=_run, name=f"llm-warmup-{key}", daemon=True).start()


def _parse_customer_response(raw: str | None) -> dict[str, Any] | None:
    """Parse LLM customer response JSON. Returns {"intents": [...], "follow_up": "..."} or None.

    Uses the shared three-tier lenient parser (json → json_repair → code block).
    When parsing fails entirely, the raw text is only accepted as a plain-text
    follow-up if it does NOT look like broken JSON/markdown — a malformed JSON
    blob must never be spoken to the user as the customer's line; returning
    None lets the dialog manager fall back to the probe templates instead.
    """
    if not raw:
        return None
    data, _method = parse_json_lenient(raw)
    if data is None:
        text = clean_plain_text(raw)
        if not text or text.lstrip().startswith(("{", "[", "```")):
            logger.warning("customer LLM output unparseable and JSON-like; using template fallback")
            return None
        return {"intents": [], "follow_up": text}

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
