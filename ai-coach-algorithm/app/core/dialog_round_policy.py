from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


MIN_DIALOG_ROUNDS = 6
MAX_DIALOG_ROUNDS = 10
DEFAULT_TARGET_ROUNDS = 8

_LOW_DIFFICULTIES = {"low", "LOW", "低"}
_HIGH_DIFFICULTIES = {"high", "HIGH", "高"}
_COMPLEX_DIRECTIONS = {"objection", "close", "compliance"}
_MEDIUM_DIRECTIONS = {"needs", "product"}
_LIGHT_DIRECTIONS = {"customer_touch", "service"}


@dataclass(frozen=True)
class DialogRoundPolicy:
    min_rounds: int
    target_rounds: int
    max_rounds: int
    source: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp_rounds(value: int, low: int = MIN_DIALOG_ROUNDS, high: int = MAX_DIALOG_ROUNDS) -> int:
    return max(low, min(high, int(value)))


def _normalize_difficulty(difficulty: str | None) -> str:
    value = str(difficulty or "").strip()
    if value in _LOW_DIFFICULTIES:
        return "low"
    if value in _HIGH_DIFFICULTIES:
        return "high"
    return "medium"


def build_dialog_round_policy(
    *,
    direction: str | None = None,
    difficulty: str | None = None,
    expected_intents: list[str] | None = None,
    scene_id: str | None = None,
) -> DialogRoundPolicy:
    """Choose the recommended 6-10 round training length.

    The policy is intentionally deterministic and cheap. The public dialogue
    API no longer accepts a caller-controlled round count; every normal session
    uses this recommendation.
    """
    direction_key = str(direction or "").strip()
    difficulty_key = _normalize_difficulty(difficulty)
    intents = set(expected_intents or [])
    scene_value = str(scene_id or "")

    if direction_key in _COMPLEX_DIRECTIONS or "compliance_sensitive" in intents:
        min_rounds, target_rounds, max_rounds = 8, 9, 10
        reason = "complex_direction_or_compliance"
    elif direction_key in _MEDIUM_DIRECTIONS:
        min_rounds, target_rounds, max_rounds = 6, 7, 8
        reason = "medium_training_direction"
    elif direction_key in _LIGHT_DIRECTIONS or scene_value.endswith("_INVITE"):
        min_rounds, target_rounds, max_rounds = 6, 6, 8
        reason = "light_touch_or_service_direction"
    else:
        min_rounds, target_rounds, max_rounds = 6, DEFAULT_TARGET_ROUNDS, 9
        reason = "default_dynamic_dialogue"

    if difficulty_key == "high":
        target_rounds = max(target_rounds, min(max_rounds, target_rounds + 1))
    elif difficulty_key == "low":
        target_rounds = min(target_rounds, min_rounds)

    if len(intents) >= 3:
        target_rounds = max(target_rounds, min(max_rounds, 8))

    target_rounds = _clamp_rounds(target_rounds, min_rounds, max_rounds)
    return DialogRoundPolicy(
        min_rounds=min_rounds,
        target_rounds=target_rounds,
        max_rounds=max_rounds,
        source="dynamic_policy",
        reason=reason,
    )
