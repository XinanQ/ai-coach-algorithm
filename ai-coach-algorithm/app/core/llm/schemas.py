"""Pydantic output models for LLM responses.

Catches both *syntactic* errors (handled in parser.py via json-repair) and
*semantic* errors here (scores out of range, internal contradictions).

The consistency check is the most important guard against the worst class of
hallucination: an LLM scoring `合规度=100` while *also* listing `合规风险` in
weakness_tags. That answer parses fine as JSON but is internally incoherent,
and would have been treated as a high-quality scoring result by a naive
parser. Pydantic's model_validator catches it before it leaves this module.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# Dimension keys must match rule_scorer.DIMENSION_DEFS, otherwise the presenter
# layer's mapping will silently drop dimensions.
DIMENSION_KEYS = ("compliance", "objection_handling", "logic_structure", "empathy")


class LLMScoreOutput(BaseModel):
    """Raw shape the LLM must return for both reply (liveScore) and finish."""

    dimension_scores: dict[str, int] = Field(
        ..., description="0-100 per dimension, keyed by DIMENSION_KEYS"
    )
    weakness_tags: list[str] = Field(default_factory=list, max_length=8)
    missing_points: list[str] = Field(default_factory=list, max_length=10)
    risk_terms: list[str] = Field(default_factory=list, max_length=10)
    suggestion: str = Field(default="", max_length=300)

    @field_validator("dimension_scores")
    @classmethod
    def _scores_in_range(cls, v: dict[str, int]) -> dict[str, int]:
        # Coerce loose types (LLM sometimes returns "85" instead of 85, or floats).
        cleaned: dict[str, int] = {}
        for key, raw in v.items():
            try:
                score = int(round(float(raw)))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"dimension '{key}' = {raw!r} is not numeric") from exc
            if not 0 <= score <= 100:
                raise ValueError(f"dimension '{key}' = {score} out of [0, 100]")
            cleaned[key] = score
        # Allow missing dimensions (will be defaulted to 0 downstream) but
        # reject anything outside the known set — those are LLM hallucinations.
        unknown = set(cleaned) - set(DIMENSION_KEYS)
        if unknown:
            raise ValueError(f"unknown dimension keys: {sorted(unknown)}")
        return cleaned

    @model_validator(mode="after")
    def _internal_consistency(self) -> "LLMScoreOutput":
        """Catch the canonical hallucination: high compliance score + 合规 weakness tag."""
        compliance = self.dimension_scores.get("compliance", 0)
        if compliance >= 85:
            offending = [tag for tag in self.weakness_tags if "合规" in tag or "风险" in tag]
            if offending:
                raise ValueError(
                    f"compliance={compliance} but weakness_tags contain "
                    f"compliance-related entries {offending} — internal contradiction"
                )
            offending_risks = [t for t in self.risk_terms if t]
            if offending_risks:
                raise ValueError(
                    f"compliance={compliance} but risk_terms is non-empty "
                    f"({offending_risks}) — internal contradiction"
                )
        return self


class LLMCustomerOutput(BaseModel):
    """Customer follow-up shape.

    The LLM emits plain text, so this is mostly a holder used by tests / future
    structured-output paths. The customer pipeline does not call Pydantic at
    runtime today — parser.parse_plain_text handles light cleanup.
    """

    content: str = Field(..., min_length=1, max_length=200)
    in_character: Literal[True] = True
