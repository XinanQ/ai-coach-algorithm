"""Observability endpoints for the LLM subsystem.

GET /metrics/llm  — process-level aggregates per (method, scene)
POST /metrics/llm/reset — wipe in-memory aggregates (handy in demos)

Not authenticated and not persisted by design. Production observability should
ship the structured `ai_coach.llm` logger to a real metrics backend instead.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.llm.metrics import get_metrics_snapshot, reset_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/llm")
def llm_metrics() -> dict[str, object]:
    """Aggregate LLM call stats (totals + per (method, scene) buckets).

    Key fields per bucket:
      - call_count, success_count, success_rate, rate_limited_count
      - input_tokens / output_tokens / cached_tokens
      - cache_hit_rate (cached_tokens / input_tokens; > 0 confirms DeepSeek
        prompt prefix caching is working — 5-layer prompt has static layers
        first so the cache key matches across requests)
      - avg_latency_ms
      - errors: dict of error_type -> count
    """
    return get_metrics_snapshot()


@router.post("/llm/reset")
def llm_metrics_reset() -> dict[str, object]:
    """Wipe in-memory aggregates. Useful before a demo to see clean numbers."""
    reset_metrics()
    return {"status": "reset"}
