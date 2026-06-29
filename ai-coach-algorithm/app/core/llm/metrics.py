"""LLM call observability: structured logging + process-level aggregation.

Two outputs from every LLM call:

1. **Structured log line** (via stdlib `logging`):
     - timestamp, scene_id, method, model
     - input_tokens / output_tokens / cached_tokens / cache_hit_rate
     - latency_ms, success, error_type
   Log format is JSON-friendly via `extra=` so any downstream log
   aggregator (Loki, ELK, CloudWatch) can parse it without regex.

2. **Process-level counters** (in-memory):
     - rolling totals per (scene_id, method) bucket
     - exposed via `get_metrics_snapshot()` for the /metrics/llm endpoint
   Reset by restarting the process; not persisted by design (this is dev/demo
   observability, not production billing — for billing route logs to a real
   metrics backend).

Why log + aggregate (not just one): logs are searchable per-call (debugging
"why was this scoring weird"), aggregates are a glance-able health snapshot
(is cache working? what's our p50 latency? error rate?).
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

logger = logging.getLogger("ai_coach.llm")


@dataclass
class CallRecord:
    """One LLM call's observability data."""

    method: str           # "finish" | "reply" | "customer" — the calling site
    scene_id: str | None  # scene context if known
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # how many input tokens were served from cache
    latency_ms: int = 0
    success: bool = False
    error_type: str | None = None
    retry_count: int = 0
    rate_limited: bool = False

    @property
    def cache_hit_rate(self) -> float:
        """Fraction of input tokens that hit the cache (0.0–1.0)."""
        if self.input_tokens <= 0:
            return 0.0
        return round(self.cached_tokens / self.input_tokens, 4)

    def as_log_extra(self) -> dict[str, Any]:
        return {
            "llm_method": self.method,
            "llm_scene_id": self.scene_id,
            "llm_model": self.model,
            "llm_input_tokens": self.input_tokens,
            "llm_output_tokens": self.output_tokens,
            "llm_cached_tokens": self.cached_tokens,
            "llm_cache_hit_rate": self.cache_hit_rate,
            "llm_latency_ms": self.latency_ms,
            "llm_success": self.success,
            "llm_error_type": self.error_type,
            "llm_retry_count": self.retry_count,
            "llm_rate_limited": self.rate_limited,
        }


# Process-level aggregator. Locked because async tasks run on one thread but we
# also want to be safe if anyone spawns workers.
_lock = Lock()
_aggregates: dict[tuple[str, str | None], dict[str, Any]] = defaultdict(
    lambda: {
        "call_count": 0,
        "success_count": 0,
        "rate_limited_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_tokens": 0,
        "total_latency_ms": 0,
        "errors": defaultdict(int),
    }
)


def _record(rec: CallRecord) -> None:
    """Log + aggregate one call. Called from llm_call_tracker on exit."""
    logger.info("llm_call", extra=rec.as_log_extra())
    key = (rec.method, rec.scene_id)
    with _lock:
        bucket = _aggregates[key]
        bucket["call_count"] += 1
        if rec.success:
            bucket["success_count"] += 1
        if rec.rate_limited:
            bucket["rate_limited_count"] += 1
        bucket["input_tokens"] += rec.input_tokens
        bucket["output_tokens"] += rec.output_tokens
        bucket["cached_tokens"] += rec.cached_tokens
        bucket["total_latency_ms"] += rec.latency_ms
        if rec.error_type:
            bucket["errors"][rec.error_type] += 1


@asynccontextmanager
async def llm_call_tracker(method: str, scene_id: str | None, model: str):
    """Context manager that times an LLM call and records the result.

    Usage:
        async with llm_call_tracker("finish", scene_id, model) as rec:
            resp = await client.chat.completions.create(...)
            rec.input_tokens = resp.usage.prompt_tokens
            rec.output_tokens = resp.usage.completion_tokens
            rec.cached_tokens = getattr(resp.usage, "prompt_cache_hit_tokens", 0) or 0
            rec.success = True

    On exception: success stays False, error_type is set from the exception
    class name, and the record is still emitted (so we see failures in metrics).
    """
    rec = CallRecord(method=method, scene_id=scene_id, model=model)
    start = time.perf_counter()
    try:
        yield rec
    except Exception as exc:
        rec.error_type = type(exc).__name__
        raise
    finally:
        rec.latency_ms = int((time.perf_counter() - start) * 1000)
        _record(rec)


def get_metrics_snapshot() -> dict[str, Any]:
    """Return a dict suitable for /metrics/llm — aggregates per (method, scene)."""
    with _lock:
        buckets = []
        for (method, scene_id), data in _aggregates.items():
            call_count = data["call_count"]
            input_tokens = data["input_tokens"]
            buckets.append({
                "method": method,
                "scene_id": scene_id,
                "call_count": call_count,
                "success_count": data["success_count"],
                "success_rate": round(data["success_count"] / call_count, 4) if call_count else 0.0,
                "rate_limited_count": data["rate_limited_count"],
                "input_tokens": input_tokens,
                "output_tokens": data["output_tokens"],
                "cached_tokens": data["cached_tokens"],
                "cache_hit_rate": round(data["cached_tokens"] / input_tokens, 4) if input_tokens else 0.0,
                "avg_latency_ms": int(data["total_latency_ms"] / call_count) if call_count else 0,
                "errors": dict(data["errors"]),
            })
    totals = {
        "call_count": sum(b["call_count"] for b in buckets),
        "input_tokens": sum(b["input_tokens"] for b in buckets),
        "output_tokens": sum(b["output_tokens"] for b in buckets),
        "cached_tokens": sum(b["cached_tokens"] for b in buckets),
    }
    if totals["input_tokens"]:
        totals["cache_hit_rate"] = round(totals["cached_tokens"] / totals["input_tokens"], 4)
    else:
        totals["cache_hit_rate"] = 0.0
    return {"totals": totals, "by_bucket": buckets}


def reset_metrics() -> None:
    """Clear all aggregates — useful in tests."""
    with _lock:
        _aggregates.clear()
