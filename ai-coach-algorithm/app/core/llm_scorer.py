"""LLM-based scorer for finish + per-turn liveScore (async).

Uses DeepSeek (OpenAI-compatible, AsyncOpenAI client) to grade an employee
answer on the same four dimensions as `rule_scorer`. Returns the same dict
shape so the dialog_manager can swap them transparently. Failure paths:

  - no API key / sdk missing       → returns None (caller falls back to rule)
  - network / timeout / 5xx        → returns None
  - JSON parse fails               → tries json-repair, then code-block extract
  - schema validation fails        → ONE retry with corrective message, then None

The async client unblocks the FastAPI event loop so concurrent dialogs don't
queue behind each other on LLM I/O. Combined with `asyncio.gather` in the
caller, the per-reply latency (scorer + customer in parallel) drops ~50%.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.llm.client import DEFAULT_MODEL, get_async_client, is_llm_available
from app.core.llm.metrics import llm_call_tracker
from app.core.llm.parser import parse_and_validate
from app.core.llm.prompts.scorer import get_finish_builder_for_scene, get_reply_builder_for_scene
from app.core.llm.retry import call_with_retry
from app.core.llm.schemas import LLMScoreOutput
from app.core.rule_scorer import DIMENSION_DEFS
from app.core.scoring_criteria_loader import get_primary_criterion

logger = logging.getLogger(__name__)

# Dimension keys / weights must match rule_scorer so the output is drop-in
# compatible. The LLM is asked to fill these exact keys.
_DIMENSION_NAMES = {key: name for key, name, _ in DIMENSION_DEFS}
_DIMENSION_WEIGHTS = {key: weight for key, _, weight in DIMENSION_DEFS}

# Tunable via env so scoring behavior can be A/B'd without code changes.
# temperature 0.0 = reproducible judgment; max_tokens 0 = no cap.
_SCORER_TEMPERATURE = float(os.getenv("AI_COACH_SCORER_TEMPERATURE", "0.0"))
_SCORER_MAX_TOKENS = int(os.getenv("AI_COACH_SCORER_MAX_TOKENS", "800"))
_CUSTOMER_MAX_TOKENS = int(os.getenv("AI_COACH_CUSTOMER_MAX_TOKENS", "300"))
# Customer replies are user-facing with a template fallback: give them a
# tighter per-request timeout than the global client default (finish scoring
# keeps the 20s default — nobody is staring at a spinner during finish).
# 0 = use the client default.
_CUSTOMER_TIMEOUT_SECONDS = float(os.getenv("AI_COACH_CUSTOMER_LLM_TIMEOUT", "10"))

# Builders are now per-scene (cached by scene_id inside the prompt module).
# Each scene gets its own ScorerSceneAnchorLayer containing the scene rubric
# baked into a static layer — DeepSeek prefix cache then hits across all calls
# to the same scene.


def _clamp_score(value: Any) -> int:
    try:
        return int(max(0, min(100, round(float(value)))))
    except (TypeError, ValueError):
        return 0


async def _call_llm_json_raw(
    messages: list[dict[str, str]],
    method: str,
    scene_id: str | None = None,
    model: str | None = None,
) -> str | None:
    """Single async LLM call asking for JSON. Returns raw text or None on transport failure.

    Wraps the actual API call in:
      1. retry policy (rate-limit aware, exponential backoff)
      2. metrics tracker (records tokens / latency / cache hit / errors)
    On terminal failure returns None — caller falls back to rule scorer.
    """
    client = get_async_client()
    if client is None:
        return None
    chosen_model = model or DEFAULT_MODEL

    async with llm_call_tracker(method=method, scene_id=scene_id, model=chosen_model) as rec:
        def on_retry(_attempt: int, exc: BaseException) -> None:
            if type(exc).__name__ == "RateLimitError":
                rec.rate_limited = True
            rec.retry_count += 1

        async def do_call():
            kwargs: dict[str, Any] = {
                "model": chosen_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                # Scoring is a judgment task, not generation — 0.0 keeps repeat
                # runs of the same dialog reproducible.
                "temperature": _SCORER_TEMPERATURE,
            }
            # Cap kills pathological long generations that blow latency; 0 disables.
            if _SCORER_MAX_TOKENS > 0:
                kwargs["max_tokens"] = _SCORER_MAX_TOKENS
            return await client.chat.completions.create(**kwargs)

        try:
            resp = await call_with_retry(do_call, label=f"llm_json/{method}", on_retry=on_retry)
        except Exception as exc:
            logger.warning("LLM scoring transport failed: %s", exc)
            return None

        usage = getattr(resp, "usage", None)
        if usage is not None:
            rec.input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            rec.output_tokens = getattr(usage, "completion_tokens", 0) or 0
            # DeepSeek-specific: prompt_cache_hit_tokens; falls back to 0 on other providers
            rec.cached_tokens = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
        rec.success = True
    return resp.choices[0].message.content or ""


async def _call_llm_text(
    messages: list[dict[str, str]],
    method: str = "customer",
    scene_id: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
) -> str | None:
    """Async LLM call returning plain text. Reused by llm_customer.

    Same retry + metrics wrapping as the JSON path. `method` defaults to
    "customer" since llm_customer is the only consumer of the plain-text variant.
    """
    client = get_async_client()
    if client is None:
        return None
    chosen_model = model or DEFAULT_MODEL

    async with llm_call_tracker(method=method, scene_id=scene_id, model=chosen_model) as rec:
        def on_retry(_attempt: int, exc: BaseException) -> None:
            if type(exc).__name__ == "RateLimitError":
                rec.rate_limited = True
            rec.retry_count += 1

        async def do_call():
            kwargs: dict[str, Any] = {
                "model": chosen_model,
                "messages": messages,
                "temperature": temperature,
            }
            # Customer follow-up is one sentence plus a small intents JSON;
            # capping output shortens the per-turn latency tail. 0 disables.
            if _CUSTOMER_MAX_TOKENS > 0:
                kwargs["max_tokens"] = _CUSTOMER_MAX_TOKENS
            if _CUSTOMER_TIMEOUT_SECONDS > 0:
                kwargs["timeout"] = _CUSTOMER_TIMEOUT_SECONDS
            return await client.chat.completions.create(**kwargs)

        try:
            resp = await call_with_retry(
                do_call, label=f"llm_text/{method}", on_retry=on_retry, retry_timeouts=False
            )
        except Exception as exc:
            logger.warning("LLM text call failed: %s", exc)
            return None

        usage = getattr(resp, "usage", None)
        if usage is not None:
            rec.input_tokens = getattr(usage, "prompt_tokens", 0) or 0
            rec.output_tokens = getattr(usage, "completion_tokens", 0) or 0
            rec.cached_tokens = getattr(usage, "prompt_cache_hit_tokens", 0) or 0
        rec.success = True
    return resp.choices[0].message.content


async def _call_llm_text_stream(
    messages: list[dict[str, str]],
    method: str = "customer",
    scene_id: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
):
    """Async generator that yields text chunks as they arrive from the LLM.

    Same retry logic for the initial connection; once streaming starts,
    transport errors surface as StopAsyncIteration (caller handles gracefully).
    Metrics are recorded after the stream is fully consumed.
    """
    client = get_async_client()
    if client is None:
        return
    chosen_model = model or DEFAULT_MODEL

    async with llm_call_tracker(method=f"{method}_stream", scene_id=scene_id, model=chosen_model) as rec:
        def on_retry(_attempt: int, exc: BaseException) -> None:
            if type(exc).__name__ == "RateLimitError":
                rec.rate_limited = True
            rec.retry_count += 1

        async def do_call():
            kwargs: dict[str, Any] = {
                "model": chosen_model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            if _CUSTOMER_MAX_TOKENS > 0:
                kwargs["max_tokens"] = _CUSTOMER_MAX_TOKENS
            if _CUSTOMER_TIMEOUT_SECONDS > 0:
                kwargs["timeout"] = _CUSTOMER_TIMEOUT_SECONDS
            return await client.chat.completions.create(**kwargs)

        try:
            stream = await call_with_retry(
                do_call, label=f"llm_text_stream/{method}", on_retry=on_retry, retry_timeouts=False
            )
        except Exception as exc:
            logger.warning("LLM stream call failed: %s", exc)
            return

        try:
            async for chunk in stream:
                if chunk.usage is not None:
                    rec.input_tokens = getattr(chunk.usage, "prompt_tokens", 0) or 0
                    rec.output_tokens = getattr(chunk.usage, "completion_tokens", 0) or 0
                    rec.cached_tokens = getattr(chunk.usage, "prompt_cache_hit_tokens", 0) or 0
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
            rec.success = True
        except Exception as exc:
            logger.warning("LLM stream interrupted: %s", exc)
            rec.error_type = type(exc).__name__


async def _call_with_retry(
    messages: list[dict[str, str]],
    method: str,
    scene_id: str | None = None,
) -> LLMScoreOutput | None:
    """Call LLM, parse + validate, retry ONCE if schema validation fails.

    Distinct from `call_with_retry` in retry.py — that one handles transport
    retries (429 / 5xx). This one handles *schema* retries: the LLM returned
    valid JSON but it violated our Pydantic rules. We feed the validation
    error back to the LLM so it can self-correct (works ~70% of the time).
    """
    raw_text = await _call_llm_json_raw(messages, method=method, scene_id=scene_id)
    if raw_text is None:
        return None
    result = parse_and_validate(raw_text, LLMScoreOutput)
    if result.succeeded:
        return result.value  # type: ignore[return-value]

    if not result.is_retry_candidate:
        # Fully unparseable — retry won't help, the model likely returned prose
        logger.warning("LLM JSON unparseable; method=%s", result.parse_method)
        return None

    # JSON parsed but schema failed → retry once with the error fed back in
    logger.info("LLM output failed schema validation, retrying once: %s", result.error)
    retry_messages = [
        *messages,
        {"role": "assistant", "content": raw_text},
        {
            "role": "user",
            "content": (
                "你上次返回的 JSON 违反了输出规范:\n"
                f"{result.error}\n\n"
                "请重新输出严格符合规范的 JSON。注意:\n"
                "- 所有 dimension_scores 值必须是 0-100 的整数\n"
                "- compliance ≥85 时,weakness_tags 不能包含'合规'相关条目,risk_terms 必须为空\n"
                "- 只输出 JSON,不要任何前后缀文字"
            ),
        },
    ]
    raw_text2 = await _call_llm_json_raw(retry_messages, method=f"{method}_schemafix", scene_id=scene_id)
    if raw_text2 is None:
        return None
    result2 = parse_and_validate(raw_text2, LLMScoreOutput)
    if result2.succeeded:
        return result2.value  # type: ignore[return-value]
    logger.warning("LLM retry also failed: %s", result2.error)
    return None


def _shape_result(parsed: LLMScoreOutput, answer: str, method: str) -> dict[str, Any]:
    """Map validated Pydantic model into rule_scorer.score_employee_answer's dict shape."""
    raw_dims = parsed.dimension_scores
    scores = {key: _clamp_score(raw_dims.get(key, 0)) for key in _DIMENSION_NAMES}
    total = _clamp_score(sum(scores[key] * _DIMENSION_WEIGHTS[key] for key in scores))
    dimension_scores = [
        {"key": key, "name": _DIMENSION_NAMES[key], "score": scores[key], "weight": _DIMENSION_WEIGHTS[key]}
        for key in _DIMENSION_NAMES
    ]
    return {
        "total_score": total,
        "dimension_scores": dimension_scores,
        "matched_terms": [],
        "risk_terms": parsed.risk_terms,
        "missing_points": parsed.missing_points,
        "weakness_tags": parsed.weakness_tags,
        "suggestion": parsed.suggestion.strip(),
        "intent_understanding": analyze_customer_answer(answer),
        "method": method,
    }


# Prompt construction lives in app.core.llm.prompts.scorer (5-layer architecture).
# This module composes builders + Pydantic validation + retry — the prompt body
# is no longer hand-spliced here.


async def score_with_llm_finish(
    answer: str,
    reference_items: list[dict[str, Any]] | None = None,
    criterion: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
    dialog_pairs: list[dict[str, Any]] | None = None,
    scene_id: str | None = None,
    weakness_prompt: str = "",
) -> dict[str, Any] | None:
    """Full LLM scoring at finish time (async, 5-layer prompt, schema retry)."""
    if not is_llm_available() or not answer.strip():
        return None
    if scene_id is None and criterion:
        scene_id = criterion.get("scene_id")
    builder = get_finish_builder_for_scene(criterion, scene_id)
    messages = builder.to_chat_messages({
        "answer": answer,
        "reference_items": reference_items,
        "coverage": coverage,
        "dialog_pairs": dialog_pairs,
        "weakness_prompt": weakness_prompt,
    })
    parsed = await _call_with_retry(messages, method="finish", scene_id=scene_id)
    if parsed is None:
        return None
    return _shape_result(parsed, answer, method="llm_scorer_deepseek_finish")


async def score_with_llm_reply(
    answer: str,
    reference_items: list[dict[str, Any]] | None = None,
    scene_id: str | None = None,
    weakness_prompt: str = "",
) -> dict[str, Any] | None:
    """Lightweight LLM scoring per turn for liveScore (5-layer prompt, schema retry)."""
    if not is_llm_available() or not answer.strip():
        return None
    criterion = get_primary_criterion(scene_id) if scene_id else None
    builder = get_reply_builder_for_scene(criterion, scene_id)
    messages = builder.to_chat_messages({
        "answer": answer,
        "reference_items": reference_items,
        "weakness_prompt": weakness_prompt,
    })
    parsed = await _call_with_retry(messages, method="reply", scene_id=scene_id)
    if parsed is None:
        return None
    return _shape_result(parsed, answer, method="llm_scorer_deepseek_reply")
