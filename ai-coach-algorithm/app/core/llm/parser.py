"""Three-tier defensive parsing for LLM JSON output.

Tier 1: `json.loads` — fast path, works when the LLM behaves
Tier 2: `json_repair.loads` — fixes common malformations (trailing commas,
        missing quotes, smart-quote substitutions, unicode escape issues)
Tier 3: Pydantic schema validation (semantic checks: range, internal
        consistency). Failure here is *not* a parse failure but a content
        failure — caller may want to retry with a corrective hint.

The `parse_and_validate` entrypoint returns a tagged result so the caller can
distinguish: parsed-and-valid / parsed-but-invalid (retry candidate) / fully
unparseable (fall back).
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class ParseResult:
    """Outcome of a parse + validate attempt.

    Exactly one of `value` / `raw` / nothing is set:
      - `value` set        → fully parsed + validated
      - `raw` set but value None → JSON parsed but schema failed (retry candidate)
      - both None          → fully unparseable
    """

    value: BaseModel | None = None
    raw: dict[str, Any] | None = None
    parse_method: str = "none"  # "json" | "json_repair" | "code_block_extract" | "none"
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return self.value is not None

    @property
    def is_retry_candidate(self) -> bool:
        """JSON parsed OK but schema validation failed — worth one retry."""
        return self.raw is not None and self.value is None


# Matches a JSON code block (```json ... ``` or just ``` ... ```) so we can pull
# the JSON out of an over-eager LLM that wraps it in markdown.
_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _try_json(text: str) -> dict[str, Any] | None:
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return result if isinstance(result, dict) else None


def _try_json_repair(text: str) -> dict[str, Any] | None:
    try:
        from json_repair import loads as repair_loads
    except ImportError:
        return None
    try:
        result = repair_loads(text)
    except Exception:  # json-repair raises various, swallow all
        return None
    return result if isinstance(result, dict) else None


def _try_extract_code_block(text: str) -> dict[str, Any] | None:
    """Some LLMs return ```json {...}``` despite being told not to. Pull it out."""
    match = _CODE_BLOCK_RE.search(text or "")
    if not match:
        return None
    inner = match.group(1)
    return _try_json(inner) or _try_json_repair(inner)


def parse_json_lenient(text: str | None) -> tuple[dict[str, Any] | None, str]:
    """Best-effort JSON dict extraction. Returns (parsed_or_None, method_label)."""
    if not text:
        return None, "none"
    parsed = _try_json(text)
    if parsed is not None:
        return parsed, "json"
    parsed = _try_json_repair(text)
    if parsed is not None:
        return parsed, "json_repair"
    parsed = _try_extract_code_block(text)
    if parsed is not None:
        return parsed, "code_block_extract"
    return None, "none"


def parse_and_validate(text: str | None, schema: Type[T]) -> ParseResult:
    """Full pipeline: JSON parse (lenient) → Pydantic validate.

    The schema's own validators (e.g. internal consistency) run here, so a
    response that parses as JSON but fails business rules surfaces as a
    `retry candidate` rather than a generic parse failure.
    """
    raw, method = parse_json_lenient(text)
    if raw is None:
        return ParseResult(parse_method="none", error="could not parse as JSON")
    try:
        value = schema.model_validate(raw)
    except ValidationError as exc:
        # Build a compact error message we can hand back to the LLM on retry.
        compact_errs = []
        for err in exc.errors()[:5]:
            loc = ".".join(str(p) for p in err.get("loc", []))
            compact_errs.append(f"{loc}: {err.get('msg', '')}")
        return ParseResult(
            raw=raw,
            parse_method=method,
            error="; ".join(compact_errs),
        )
    return ParseResult(value=value, raw=raw, parse_method=method)


def clean_plain_text(text: str | None) -> str | None:
    """Light cleanup for non-JSON outputs (e.g. customer follow-up message).

    Strips quoting wrappers the model sometimes adds despite instructions
    ("..." / 「...」 / 『...』) and surrounding whitespace.
    """
    if not text:
        return None
    cleaned = text.strip().strip("\"'「」『』").strip()
    return cleaned or None
