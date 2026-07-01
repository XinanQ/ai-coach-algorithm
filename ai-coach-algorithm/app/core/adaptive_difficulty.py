"""自适应难度推荐模块（Layer 3）。

根据用户在特定场景下的近期训练成绩，自动推荐下一次训练的难度等级：
  - 连续 ≥85 分 (N=3) → 推荐升难度
  - 连续 <60 分 (N=2) → 推荐降难度
  - 其他 → 维持当前难度

同时输出针对性训练建议（哪些维度需要专项加强）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.memory_manager import get_memory_manager

DIFFICULTY_LEVELS = ["低", "中", "高"]
UPGRADE_THRESHOLD = 85
UPGRADE_STREAK = 3
DOWNGRADE_THRESHOLD = 60
DOWNGRADE_STREAK = 2


@dataclass
class DifficultyRecommendation:
    user_id: str
    scene_id: str
    current_difficulty: str
    recommended_difficulty: str
    reason: str
    session_count: int = 0
    recent_scores: list[float] = field(default_factory=list)
    weak_dimensions: list[str] = field(default_factory=list)
    training_suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "scene_id": self.scene_id,
            "current_difficulty": self.current_difficulty,
            "recommended_difficulty": self.recommended_difficulty,
            "reason": self.reason,
            "session_count": self.session_count,
            "recent_scores": self.recent_scores,
            "weak_dimensions": self.weak_dimensions,
            "training_suggestion": self.training_suggestion,
        }


def _next_difficulty(current: str, direction: int) -> str:
    idx = DIFFICULTY_LEVELS.index(current) if current in DIFFICULTY_LEVELS else 1
    new_idx = max(0, min(len(DIFFICULTY_LEVELS) - 1, idx + direction))
    return DIFFICULTY_LEVELS[new_idx]


def recommend_difficulty(
    user_id: str,
    scene_id: str,
    current_difficulty: str = "中",
    limit: int = 10,
) -> DifficultyRecommendation:
    manager = get_memory_manager()
    records = manager.list_longterm(user_id=user_id, scenario_id=scene_id, limit=limit)

    if not records:
        return DifficultyRecommendation(
            user_id=user_id,
            scene_id=scene_id,
            current_difficulty=current_difficulty,
            recommended_difficulty=current_difficulty,
            reason="无历史训练记录，维持默认难度",
        )

    records = sorted(
        records,
        key=lambda r: r.get("saved_at") or r.get("updated_at") or "",
    )

    scores = [float(r["score"]) for r in records if r.get("score") is not None]
    if not scores:
        return DifficultyRecommendation(
            user_id=user_id,
            scene_id=scene_id,
            current_difficulty=current_difficulty,
            recommended_difficulty=current_difficulty,
            reason="历史记录无有效评分",
            session_count=len(records),
        )

    recent = scores[-max(UPGRADE_STREAK, DOWNGRADE_STREAK):]

    upgrade = len(recent) >= UPGRADE_STREAK and all(
        s >= UPGRADE_THRESHOLD for s in recent[-UPGRADE_STREAK:]
    )
    downgrade = len(recent) >= DOWNGRADE_STREAK and all(
        s < DOWNGRADE_THRESHOLD for s in recent[-DOWNGRADE_STREAK:]
    )

    dim_scores: dict[str, list[float]] = {}
    for rec in records:
        for dim in (rec.get("score_result") or {}).get("dimension_scores") or []:
            key = dim.get("key") or dim.get("name", "")
            val = dim.get("score")
            if key and val is not None:
                dim_scores.setdefault(key, []).append(float(val))

    weak_dims = [
        k for k, vals in dim_scores.items()
        if len(vals) >= 2 and (sum(vals[-3:]) / len(vals[-3:])) < 60
    ]

    if upgrade:
        rec_diff = _next_difficulty(current_difficulty, +1)
        reason = f"最近 {UPGRADE_STREAK} 次得分均 ≥{UPGRADE_THRESHOLD}，建议提升难度"
    elif downgrade:
        rec_diff = _next_difficulty(current_difficulty, -1)
        reason = f"最近 {DOWNGRADE_STREAK} 次得分均 <{DOWNGRADE_THRESHOLD}，建议降低难度"
    else:
        rec_diff = current_difficulty
        reason = "成绩波动正常，维持当前难度"

    suggestion = ""
    if weak_dims:
        suggestion = f"建议专项加强：{'、'.join(weak_dims[:3])}"
    elif downgrade:
        suggestion = "建议先用低难度客户巩固基础话术，再逐步提升"
    elif upgrade and rec_diff == current_difficulty:
        suggestion = "已达最高难度，建议尝试不同场景拓展能力边界"

    return DifficultyRecommendation(
        user_id=user_id,
        scene_id=scene_id,
        current_difficulty=current_difficulty,
        recommended_difficulty=rec_diff,
        reason=reason,
        session_count=len(records),
        recent_scores=[round(s, 1) for s in recent],
        weak_dimensions=weak_dims[:5],
        training_suggestion=suggestion,
    )
