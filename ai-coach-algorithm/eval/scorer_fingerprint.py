"""Scorer configuration fingerprint — makes the frozen baseline enforceable.

The 50-case scorer baseline (score_band_pass 0.94) is only valid for the
exact scorer that produced it. transcript_hash already binds the reviewed
bands to the dialog TEXT; this module binds the baseline to the scorer
CONFIGURATION: model, temperature/max_tokens, the rendered static prompt
layers, red-line terms, and the source of every scoring-critical module.

Any change to those inputs changes the fingerprint, which flips the eval
report to `baseline_fingerprint_match=false` and `citable_full_baseline=false`
— forcing a deliberate re-baseline (rerun the 50 cases, then bless the new
fingerprint) instead of silently citing a stale 0.94.

Blessing: python -m eval.stages.eval_scorer --bless-fingerprint
(only allowed on a full-gold, LLM-only run).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

BASELINE_FINGERPRINT_PATH = Path("data/eval/scorer_baseline_fingerprint.json")

# Every module whose behavior can change a finish score or its tags.
# Source-level hashing is deliberately strict: even a comment-only change
# forces a cheap re-verification run, which is the discipline we want for a
# frozen baseline.
_SCORING_CRITICAL_SOURCES = [
    "app/core/llm_scorer.py",
    "app/core/rule_scorer.py",
    "app/core/dialog_manager.py",
    "app/core/weakness_taxonomy.py",
    "app/core/llm/prompts/scorer.py",
    "app/core/llm/prompts/boundaries.py",
    "app/core/llm/prompts/scene_anchor.py",
    "app/core/llm/prompts/formats.py",
    "app/core/llm/schemas.py",
]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_scorer_config_fingerprint() -> dict[str, Any]:
    """Return {"fingerprint": <sha256>, "components": {...}} for the live scorer."""
    from app.core.llm.client import DEFAULT_MODEL
    from app.core.llm.prompts.scorer import build_finish_scorer_builder
    from app.core.llm_scorer import _SCORER_MAX_TOKENS, _SCORER_TEMPERATURE
    from app.core.rule_scorer import HIGH_RISK_TERMS
    import app.core.dialog_manager as dialog_manager

    rendered = build_finish_scorer_builder(None, None).build({})

    components: dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "temperature": _SCORER_TEMPERATURE,
        "max_tokens": _SCORER_MAX_TOKENS,
        "redline_cross_check": getattr(dialog_manager, "_REDLINE_CROSS_CHECK_ENABLED", None),
        "redline_cap": getattr(dialog_manager, "_RED_LINE_COMPLIANCE_CAP", None),
        "rendered_prompt_sha": _sha((rendered.system + "\n\n" + rendered.user).encode("utf-8")),
        "red_line_terms_sha": _sha(
            json.dumps(sorted(HIGH_RISK_TERMS), ensure_ascii=False).encode("utf-8")
        ),
    }
    source_shas: dict[str, str] = {}
    for rel in _SCORING_CRITICAL_SOURCES:
        path = Path(rel)
        source_shas[rel] = _sha(path.read_bytes()) if path.exists() else "missing"
    components["source_shas"] = source_shas

    payload = json.dumps(components, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"fingerprint": _sha(payload.encode("utf-8")), "components": components}


def load_blessed_fingerprint() -> dict[str, Any] | None:
    if not BASELINE_FINGERPRINT_PATH.exists():
        return None
    try:
        return json.loads(BASELINE_FINGERPRINT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def bless_fingerprint(current: dict[str, Any], baseline_summary: dict[str, Any]) -> None:
    """Record the current scorer config as the one the frozen baseline was measured on."""
    from datetime import datetime, timezone

    record = {
        "fingerprint": current["fingerprint"],
        "blessed_at": datetime.now(timezone.utc).isoformat(),
        "baseline_summary": baseline_summary,
        "components": current["components"],
    }
    BASELINE_FINGERPRINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FINGERPRINT_PATH.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
