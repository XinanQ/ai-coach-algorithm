"""L2 "锚定层" — 把 scene-stable 内容烤进静态前缀。

L2 上下文层正常情况下是动态的(每次调用都变),但其中有一部分内容是
**整个 scene 永远不变的**:
  - 客户画像(profile):同一个 scene 同一个客户人格
  - 评分 rubric:同一个 scene 的 must_points / red_lines 固定

这些"scene-stable"内容如果留在动态 L2 里,DeepSeek prefix cache 无法跨调用
命中。改造方案:把它们提取出来,做成"每个 scene 一个静态 builder"的
SceneAnchorLayer,放在 L2 动态内容之前。

效果:同一 scene 的多次调用,scene-anchor 字节完全一致 → 进入缓存前缀。
"""
from __future__ import annotations

from typing import Any

from app.core.llm.prompts.base import PromptLayer


class CustomerSceneAnchorLayer(PromptLayer):
    """客户模拟场景:固化客户画像到静态层。

    构造时传入 profile,render 时忽略 context — 画像在 builder 创建时已锁定。
    """

    is_dynamic = False  # ← 关键:整个 scene 内不变,可被 prefix cache 命中

    def __init__(self, profile: dict[str, Any] | None, scene_id: str | None):
        self.profile = profile or {}
        self.scene_id = scene_id or "unknown"
        # 缓存 key 包含 scene_id,builder 间不会串号
        self.name = f"L2anchor_customer__{self.scene_id}"

    def render(self, context: dict[str, Any]) -> str:
        p = self.profile
        return (
            "## L2-Anchor 你的客户画像(场景固定,沉浸式扮演)\n"
            f"- 场景 ID: {self.scene_id}\n"
            f"- 性格: {p.get('personality', '(未指定)')}\n"
            f"- 核心顾虑: {p.get('concern', '(未指定)')}\n"
            f"- 难度: {p.get('difficulty_level', '(未指定)')}\n"
            f"- 类型: {p.get('customer_type', '(未指定)')}"
        )


class ScorerSceneAnchorLayer(PromptLayer):
    """评分场景:固化 criterion(rubric)到静态层。

    构造时传入 criterion,后续所有针对该 scene 的评分都共享这段前缀。
    动态部分(员工答案 / coverage / dialog_pairs)留在 L2 动态层。
    """

    is_dynamic = False

    def __init__(self, criterion: dict[str, Any] | None, scene_id: str | None):
        self.criterion = criterion or {}
        self.scene_id = scene_id or "unknown"
        self.name = f"L2anchor_scorer__{self.scene_id}"

    def render(self, context: dict[str, Any]) -> str:
        c = self.criterion
        must_points = c.get("must_points") or []
        red_lines = c.get("compliance_red_lines") or []
        return "\n\n".join([
            "## L2-Anchor 场景评分锚点(同一 scene 内永不变)",
            f"### 场景 ID: {self.scene_id}",
            f"### 场景评分目标\n{c.get('answer_goal', '(无)')}",
            "### 标准要点(应覆盖)\n- " + "\n- ".join(must_points) if must_points else "### 标准要点\n(无)",
            "### 合规红线(踩到必须重扣)\n- " + "\n- ".join(red_lines) if red_lines else "### 合规红线\n(无)",
        ])
