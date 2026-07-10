"""评分场景的 5 层 prompt 实现 (L1+L3 共享, L2/L5 分 finish/reply)。

两个公开构造器:
  build_finish_scorer_prompt()  — 评 finish 时用,展示完整对话轨迹
  build_reply_scorer_prompt()   — 评 reply 时用,只看本轮单条回复

两者共用 L1/L3/L4/L5,只在 L2 上下文不同。所有静态层都进同一个 builder
缓存,这意味着同一进程内多个对话评分的静态部分只渲染一次。
"""
from __future__ import annotations

import json
from typing import Any

from app.core.llm.prompts.base import LayeredPromptBuilder, PromptLayer
from app.core.llm.prompts.boundaries import GlobalBoundaryLayer, ScorerBoundaryLayer
from app.core.llm.prompts.formats import ScorerFormatLayer
from app.core.llm.prompts.scene_anchor import ScorerSceneAnchorLayer


# ============================================================
# L1 系统人设层
# ============================================================

class ScorerPersonaLayer(PromptLayer):
    """L1 评分专家身份 + 最高准则。"""

    name = "L1_persona_scorer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "你是金融营销陪练系统的资深评分专家,长期为商业银行、保险公司、基金公司"
            "做销售合规和话术质量审计。你的最高准则:\n"
            "- 客观、严谨、可复核——任何评分都能指着标准要点说清楚为什么\n"
            "- 合规优先——合规问题永远比话术漂亮重要\n"
            "- 不揣测、不脑补——只评估对话里实际出现的内容"
        )


# ============================================================
# L3 核心指令层(共享)
# ============================================================

class ScorerInstructionLayer(PromptLayer):
    """L3 评分任务 + CoT 三步拆解(含示例)。"""

    name = "L3_instruction_scorer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "## L3 任务(按顺序内部完成,不要把过程输出出来)\n"
            "**第 1 步 提取**:从员工回答中抽出关键陈述,分为四类:\n"
            "  - 承诺类:涉及收益/本金安全/未来表现的肯定陈述\n"
            "  - 解释类:对产品规则、机制、风险的说明\n"
            "  - 引导类:推进客户做下一步动作(办理/查询/约时间)\n"
            "  - 共情类:认可客户顾虑、复述客户情绪的表达\n"
            "**第 2 步 分析**:逐条对照——\n"
            "  • 是否命中合规红线(`compliance_red_lines`)?\n"
            "  • 是否覆盖标准要点(`must_points`)?\n"
            "  • 结构是否符合'共情 → 解释 → 引导'?\n"
            "  • 是否真的回应了客户具体顾虑(而非堆话术词)?\n"
            "**第 3 步 总结**:综合给出 4 维度分数 + weakness_tags + suggestion。\n\n"
            "## L3 评分判断示例(供参考校准,不要复读这些示例)\n"
            "示例 1:员工说'稳赚不赔,跟存款一样'\n"
            "  → 合规度 0(踩两个红线:绝对化承诺 + 包装成存款)\n"
            "  → weakness_tags 必含:合规问题、不当承诺\n"
            "  → suggestion 必须点名'删除绝对化承诺、不能将保险类比存款'\n\n"
            "示例 2:员工说'我先了解您的资金安排,这款产品需要每年缴费,请以合同为准'\n"
            "  → 合规度 80-90(有合规揭示:以合同为准)\n"
            "  → 共情力 60-70(只在第一句做需求探询,深度不足)\n"
            "  → suggestion 应引导'先认可客户顾虑,再补充缴费期限、保障责任等要点'\n\n"
            "示例 3:员工先犯错(说'稳赚')后又改正('请以合同为准,不能承诺')\n"
            "  → 合规度仍要扣分(违规事实发生过),但 suggestion 应认可纠错行为\n\n"
            "示例 4:员工回答很短,但每句话都合规('不保本,收益不确定,以合同条款为准')\n"
            "  → compliance 可评 85-95,不能因为回答简短或其他维度较低而连坐到 30 分档\n"
            "  → objection_handling / logic_structure / empathy 仍按实际信息量分别评分,可以较低\n"
            "  → 四个维度相互独立,总分低不等于合规度必须低\n\n"
            "示例 5:员工催促客户,但没有虚假陈述或收益承诺\n"
            "  → objection_handling / empathy 应显著低分,weakness_tags 应含强推销、客户关系不佳\n"
            "  → 一般施压且仍保留客户选择权时总分通常在 15-35 分\n"
            "  → 出现'必须来/今天就签/不用和家人商量'并叠加名额稀缺时属于严重强迫成交,通常 10-25 分\n"
            "  → 不能仅因施压就把 compliance 评为 0;若同时出现稳赚、保本等红线再进一步压分\n\n"
            "## 输出原则\n"
            "只输出第 3 步的结果,不要展示提取/分析过程。"
        )


# ============================================================
# L2 上下文注入层 — finish 版(完整对话)
# ============================================================

def _format_reference_items(items: list[dict[str, Any]] | None, limit: int = 3) -> str:
    if not items:
        return "(无)"
    lines = []
    for i, item in enumerate(items[:limit], 1):
        content = str(item.get("content", "")).strip().replace("\n", " ")
        if len(content) > 240:
            content = content[:240] + "…"
        lines.append(f"{i}. {content}")
    return "\n".join(lines)


def _format_dialog_pairs(pairs: list[dict[str, Any]] | None) -> str:
    if not pairs:
        return "(无)"
    blocks = []
    for i, pair in enumerate(pairs, 1):
        q = str(pair.get("customer_question", "")).strip()
        a = str(pair.get("employee_answer", "")).strip()
        lines = [f"【第 {i} 轮】"]
        if q:
            lines.append(f"客户问: {q}")
        if a:
            lines.append(f"员工答: {a}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


class FinishContextLayer(PromptLayer):
    """L2 finish 动态上下文:coverage + 检索 + 全对话轨迹。

    rubric(answer_goal / must_points / red_lines)已经在 ScorerSceneAnchorLayer
    里固化为静态层,这里只放真正每次都不同的内容。
    """

    name = "L2_context_finish"
    is_dynamic = True  # 每次调用都不同

    def render(self, context: dict[str, Any]) -> str:
        coverage = context.get("coverage") or {}
        reference_items = context.get("reference_items") or []
        dialog_pairs = context.get("dialog_pairs") or []
        fallback_answer = context.get("answer") or ""
        weakness_prompt = context.get("weakness_prompt") or ""

        missing_texts = coverage.get("missing_texts") or []
        coverage_rate = coverage.get("coverage_rate")

        if dialog_pairs:
            answer_block = (
                "## L2.3 员工完整对话表现(按轮次)\n"
                + _format_dialog_pairs(dialog_pairs)
                + "\n\n## L2.4 评估指引\n"
                  "- 按员工**整体**对话表现打分,不要只看最后一轮\n"
                  "- 任何一轮命中合规红线,合规度按 L4 硬约束扣分\n"
                  "- 如果员工先犯错后明确改正,可以适度加分(认可纠错)\n"
                  "- 标准要点覆盖按所有员工回答的并集判断"
            )
        else:
            answer_block = f"## L2.3 员工最终回答\n{fallback_answer}"

        sections = [
            f"## L2.1 检索到的标准话术片段(供对照,不必逐条复述)\n{_format_reference_items(reference_items)}",
            "## L2.2a 客观漏答提示(算法预判,你需复核)\n"
            + ("- " + "\n- ".join(missing_texts) if missing_texts else "(无明显漏答)"),
            f"## L2.2b 客观要点覆盖率参考\n{coverage_rate if coverage_rate is not None else '(无)'}",
            answer_block,
        ]
        if weakness_prompt:
            sections.append(weakness_prompt)
        return "\n\n".join(sections)


# ============================================================
# L2 上下文注入层 — reply 版(轻量,只看本轮)
# ============================================================

class ReplyContextLayer(PromptLayer):
    """L2 reply 上下文:本轮员工回复 + 检索话术(轻量,粒度可粗)。"""

    name = "L2_context_reply"
    is_dynamic = True

    def render(self, context: dict[str, Any]) -> str:
        answer = context.get("answer") or ""
        reference_items = context.get("reference_items") or []
        weakness_prompt = context.get("weakness_prompt") or ""
        sections = [
            f"## L2.1 员工本轮回复\n{answer}",
            f"## L2.2 检索到的相关标准话术(参考)\n{_format_reference_items(reference_items, limit=2)}",
            "## L2.3 评分粒度\n本轮是 liveScore 预览,粒度可粗,但合规问题不能放过。",
        ]
        if weakness_prompt:
            sections.append(weakness_prompt)
        return "\n\n".join(sections)


# ============================================================
# Public builder factories
# ============================================================

def build_finish_scorer_builder(
    criterion: dict[str, Any] | None = None,
    scene_id: str | None = None,
) -> LayeredPromptBuilder:
    """组装 finish 评分的 5 层 builder(scene-aware,prefix-cache 友好)。

    顺序:
      system: L1 persona
      user:   L3 instruction → L4 global → L4 scorer → L5 format
              → **L2-Anchor rubric(静态,同 scene 共享)**
              → L2 context(动态)
    """
    return LayeredPromptBuilder(
        system_layer=ScorerPersonaLayer(),
        user_layers=[
            ScorerInstructionLayer(),
            GlobalBoundaryLayer(),
            ScorerBoundaryLayer(),
            ScorerFormatLayer(),
            ScorerSceneAnchorLayer(criterion, scene_id),  # 静态,锚定 scene rubric
            FinishContextLayer(),                          # 动态
        ],
    )


def build_reply_scorer_builder(
    criterion: dict[str, Any] | None = None,
    scene_id: str | None = None,
) -> LayeredPromptBuilder:
    """组装 reply liveScore 评分的 5 层 builder(scene-aware)。

    reply 没有完整 rubric 评估,但放 SceneAnchor 仍然有意义:
    LLM 知道当前是哪个 scene,可以参考红线词表打 liveScore。
    """
    return LayeredPromptBuilder(
        system_layer=ScorerPersonaLayer(),
        user_layers=[
            ScorerInstructionLayer(),
            GlobalBoundaryLayer(),
            ScorerBoundaryLayer(),
            ScorerFormatLayer(),
            ScorerSceneAnchorLayer(criterion, scene_id),  # 静态,锚定 scene
            ReplyContextLayer(),                            # 动态
        ],
    )


# Per-scene builder 缓存,同一 scene 跨调用复用静态层 → DeepSeek prefix cache 命中。
_FINISH_BUILDER_CACHE: dict[str, LayeredPromptBuilder] = {}
_REPLY_BUILDER_CACHE: dict[str, LayeredPromptBuilder] = {}


def get_finish_builder_for_scene(
    criterion: dict[str, Any] | None,
    scene_id: str | None,
) -> LayeredPromptBuilder:
    cache_key = scene_id or "default"
    if cache_key not in _FINISH_BUILDER_CACHE:
        _FINISH_BUILDER_CACHE[cache_key] = build_finish_scorer_builder(criterion, scene_id)
    return _FINISH_BUILDER_CACHE[cache_key]


def get_reply_builder_for_scene(
    criterion: dict[str, Any] | None,
    scene_id: str | None,
) -> LayeredPromptBuilder:
    cache_key = scene_id or "default"
    if cache_key not in _REPLY_BUILDER_CACHE:
        _REPLY_BUILDER_CACHE[cache_key] = build_reply_scorer_builder(criterion, scene_id)
    return _REPLY_BUILDER_CACHE[cache_key]
