"""用户弱点画像聚合模块。

从 longterm_memory 中提取用户最近 K 次训练的评分结果，聚合为：
  - 各维度平均分 + 趋势(上升/下降/持平)
  - 高频 weakness_tags（出现 ≥2 次的标签）
  - 最近一次训练摘要

输出的 WeaknessProfile 注入到 Customer/Scorer 的 L2 动态层，
让 AI 客户针对弱项加压，评分器关注是否改善了老毛病。
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.core.memory_manager import get_memory_manager


@dataclass
class WeaknessProfile:
    user_id: str
    session_count: int = 0
    avg_score: float = 0.0
    dimension_averages: dict[str, float] = field(default_factory=dict)
    dimension_trends: dict[str, str] = field(default_factory=dict)
    frequent_weakness_tags: list[str] = field(default_factory=list)
    recent_weakness_tags: list[str] = field(default_factory=list)
    recent_score: float | None = None
    recent_suggestion: str = ""

    def has_history(self) -> bool:
        return self.session_count > 0

    def to_prompt_text(self, role: str = "customer") -> str:
        """渲染为可注入 prompt 的自然语言段落。

        role="customer" → 客户视角提示(针对弱项加压)
        role="scorer"   → 评分器视角提示(关注是否改善)
        """
        if not self.has_history():
            return ""

        lines: list[str] = []

        if role == "customer":
            lines.append(f"## 历史训练画像（该员工已练习 {self.session_count} 次，平均分 {self.avg_score:.0f}）")
            if self.frequent_weakness_tags:
                lines.append(f"- 反复出现的弱项：{'、'.join(self.frequent_weakness_tags)}")
                lines.append("- **你应在对话中重点围绕这些弱项施压**，用更尖锐的追问测试员工是否改善")
            if self.recent_weakness_tags:
                lines.append(f"- 上一次训练的弱项：{'、'.join(self.recent_weakness_tags)}")
            if self._declining_dims():
                lines.append(f"- 正在退步的维度：{'、'.join(self._declining_dims())}（可加重追问力度）")

        elif role == "scorer":
            lines.append(f"## 历史训练画像（该员工已练习 {self.session_count} 次，平均分 {self.avg_score:.0f}）")
            if self.frequent_weakness_tags:
                lines.append(f"- 反复出现的弱项：{'、'.join(self.frequent_weakness_tags)}")
                lines.append("- 评分时**重点关注这些弱项是否有改善**，如果改善了请在 suggestion 中肯定进步")
            dim_lines = []
            for dim, avg in self.dimension_averages.items():
                trend = self.dimension_trends.get(dim, "持平")
                dim_lines.append(f"  {dim}: 平均 {avg:.0f} 分（{trend}）")
            if dim_lines:
                lines.append("- 各维度历史表现：\n" + "\n".join(dim_lines))
            if self.recent_suggestion:
                lines.append(f"- 上次评分建议：{self.recent_suggestion}")

        return "\n".join(lines)

    def _declining_dims(self) -> list[str]:
        return [dim for dim, trend in self.dimension_trends.items() if trend == "下降"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_count": self.session_count,
            "avg_score": round(self.avg_score, 1),
            "dimension_averages": {k: round(v, 1) for k, v in self.dimension_averages.items()},
            "dimension_trends": dict(self.dimension_trends),
            "frequent_weakness_tags": self.frequent_weakness_tags,
            "recent_weakness_tags": self.recent_weakness_tags,
            "recent_score": self.recent_score,
            "recent_suggestion": self.recent_suggestion,
        }


def _compute_trend(scores: list[float]) -> str:
    """根据最近 K 次得分判断趋势。

    策略：比较前半段均值 vs 后半段均值，差值 ≥5 判定上升/下降。
    """
    if len(scores) < 2:
        return "持平"
    mid = len(scores) // 2
    first_half = sum(scores[:mid]) / max(len(scores[:mid]), 1)
    second_half = sum(scores[mid:]) / max(len(scores[mid:]), 1)
    diff = second_half - first_half
    if diff >= 5:
        return "上升"
    elif diff <= -5:
        return "下降"
    return "持平"


def build_weakness_profile(
    user_id: str,
    scene_id: str | None = None,
    limit: int = 10,
) -> WeaknessProfile:
    """从长期记忆聚合用户弱点画像。

    Args:
        user_id: 用户 ID
        scene_id: 可选场景过滤（只看该场景的历史）
        limit: 最多回溯多少次训练
    """
    manager = get_memory_manager()
    records = manager.list_longterm(user_id=user_id, scenario_id=scene_id, limit=limit)

    if not records:
        return WeaknessProfile(user_id=user_id)

    records = sorted(records, key=lambda r: r.get("saved_at") or r.get("updated_at") or "", reverse=False)

    all_tags: list[str] = []
    total_scores: list[float] = []
    dim_scores: dict[str, list[float]] = {}

    for rec in records:
        score = rec.get("score")
        if score is not None:
            total_scores.append(float(score))

        tags = rec.get("weakness_tags") or []
        if isinstance(tags, list):
            all_tags.extend(tags)

        score_result = rec.get("score_result") or {}
        for dim_entry in score_result.get("dimension_scores") or []:
            key = dim_entry.get("key") or dim_entry.get("name", "")
            val = dim_entry.get("score")
            if key and val is not None:
                dim_scores.setdefault(key, []).append(float(val))

    tag_counter = Counter(all_tags)
    frequent_tags = [tag for tag, count in tag_counter.most_common(5) if count >= 2]

    latest = records[-1]
    recent_tags = latest.get("weakness_tags") or []
    recent_score = latest.get("score")
    recent_suggestion = (latest.get("score_result") or {}).get("suggestion", "")
    if not recent_suggestion:
        recent_suggestion = latest.get("feedback", "")

    dim_averages = {key: sum(vals) / len(vals) for key, vals in dim_scores.items() if vals}
    dim_trends = {key: _compute_trend(vals) for key, vals in dim_scores.items() if len(vals) >= 2}

    return WeaknessProfile(
        user_id=user_id,
        session_count=len(records),
        avg_score=sum(total_scores) / len(total_scores) if total_scores else 0.0,
        dimension_averages=dim_averages,
        dimension_trends=dim_trends,
        frequent_weakness_tags=frequent_tags,
        recent_weakness_tags=recent_tags if isinstance(recent_tags, list) else [],
        recent_score=recent_score,
        recent_suggestion=recent_suggestion[:200] if recent_suggestion else "",
    )
