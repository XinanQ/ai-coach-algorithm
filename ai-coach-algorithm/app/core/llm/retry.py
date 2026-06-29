"""LLM call retry policy: rate limit + transient transport errors.

Decides which exceptions are worth retrying and applies exponential backoff
with jitter. Reused by both the JSON and text call paths so the policy is
consistent across the codebase.

Retry policy:
  - RateLimitError (429)            → retry, honor Retry-After if present
  - APITimeoutError / ConnError     → retry with backoff
  - InternalServerError (5xx)       → retry with backoff
  - APIStatusError (other)          → NO retry (4xx are caller bugs)
  - BadRequestError (400)           → NO retry (prompt too long / malformed)
  - AuthenticationError (401)       → NO retry (config issue, will keep failing)
  - everything else                 → NO retry (unknown, fail loudly)

Max 3 attempts total. Backoff: 1s, 2s, 4s with ±20% jitter.
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Per-attempt cap (seconds). Includes jitter band.
_BACKOFF_BASE = 1.0
_BACKOFF_FACTOR = 2.0
_JITTER_FRACTION = 0.2
_MAX_ATTEMPTS = 3


def _is_retryable(exc: BaseException) -> bool:
    """Check if an openai-sdk exception should be retried.

    Done by class name + status_code to avoid hard-importing openai exception
    classes at module load (keeps the codebase tolerant to openai-sdk version
    drift / partial installs).
    """
    name = type(exc).__name__
    if name == "RateLimitError":
        return True
    if name in ("APITimeoutError", "APIConnectionError"):
        return True
    if name == "InternalServerError":
        return True
    # Generic APIStatusError — only retry 5xx; 4xx is a caller bug
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and 500 <= status < 600:
        return True
    return False


def _retry_after_hint(exc: BaseException) -> float | None:
    """Read Retry-After header from a 429 response if available."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    try:
        value = response.headers.get("retry-after")
    except Exception:
        return None
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _backoff_seconds(attempt: int) -> float:
    """1s, 2s, 4s with ±20% jitter (attempt is 0-indexed)."""
    base = _BACKOFF_BASE * (_BACKOFF_FACTOR ** attempt)
    jitter = base * _JITTER_FRACTION
    return max(0.1, base + random.uniform(-jitter, jitter))


async def call_with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    label: str = "llm_call",
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Run an async LLM call with rate-limit-aware retry.

    `on_retry(attempt, exc)` is a hook (used by metrics to mark rate_limited=True).
    The wrapped function takes no args — capture state in a closure.
    """
    last_exc: BaseException | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc):
                # Non-retryable — fail fast so caller can handle / fall back
                raise
            if attempt == _MAX_ATTEMPTS - 1:
                logger.warning("%s exhausted %d retries (%s)", label, _MAX_ATTEMPTS, type(exc).__name__)
                raise
            wait = _retry_after_hint(exc) or _backoff_seconds(attempt)
            logger.info(
                "%s retry %d/%d after %s (waiting %.2fs)",
                label, attempt + 1, _MAX_ATTEMPTS - 1, type(exc).__name__, wait,
            )
            if on_retry is not None:
                try:
                    on_retry(attempt, exc)
                except Exception:
                    logger.exception("on_retry hook raised")
            await asyncio.sleep(wait)
    # Unreachable, kept for type checker
    assert last_exc is not None
    raise last_exc
