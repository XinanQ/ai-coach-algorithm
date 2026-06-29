"""DeepSeek client factories (sync + async, OpenAI-compatible).

Two singletons cached on first call. The async client is what we use in the
FastAPI request path so LLM I/O doesn't block the event loop; the sync client
is kept for offline scripts that don't have an event loop.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger(__name__)

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = os.getenv("AI_COACH_LLM_MODEL", "deepseek-chat")
REQUEST_TIMEOUT = float(os.getenv("AI_COACH_LLM_TIMEOUT", "20"))

_sync_client: "OpenAI | None" = None
_async_client: "AsyncOpenAI | None" = None


def _api_key() -> str | None:
    return os.getenv("DEEPSEEK_API_KEY")


def get_sync_client() -> "OpenAI | None":
    """Sync client for offline scripts / non-async contexts."""
    global _sync_client
    if _sync_client is not None:
        return _sync_client
    key = _api_key()
    if not key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai SDK not installed; LLM disabled")
        return None
    _sync_client = OpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL, timeout=REQUEST_TIMEOUT)
    return _sync_client


def get_async_client() -> "AsyncOpenAI | None":
    """Async client — the one the FastAPI request path uses.

    Returning None on missing key is intentional: the caller decides whether
    to fall back to a rule-based path or to error out.
    """
    global _async_client
    if _async_client is not None:
        return _async_client
    key = _api_key()
    if not key:
        return None
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("openai SDK not installed; async LLM disabled")
        return None
    _async_client = AsyncOpenAI(api_key=key, base_url=DEEPSEEK_BASE_URL, timeout=REQUEST_TIMEOUT)
    return _async_client


def is_llm_available() -> bool:
    """Cheap check used by callers to decide LLM-first vs rule-fallback."""
    return _api_key() is not None
