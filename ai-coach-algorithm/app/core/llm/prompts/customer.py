"""客户模拟场景的 5 层 prompt 实现。

L1/L3/L4/L5 全静态(身份模板 + 任务 + 边界 + 格式约束),L2 是动态的
(画像 + 对话历史 + 算法 gap 分析 + RAG 检索)。
"""
from __future__ import annotations

from typing import Any

from app.core.intent_labels import INTENT_LABEL_DESCRIPTIONS
from app.core.llm.prompts.base import LayeredPromptBuilder, PromptLayer
from app.core.llm.prompts.boundaries import CustomerBoundaryLayer, GlobalBoundaryLayer
from app.core.llm.prompts.formats import CustomerFormatLayer
from app.core.llm.prompts.scene_anchor import CustomerSceneAnchorLayer


# ============================================================
# L1 系统人设层(模板,具体画像在 L2 注入)
# ============================================================

class CustomerPersonaLayer(PromptLayer):
    """L1 客户角色身份 + 沉浸式人设模板。

    具体的画像数据(personality / concern / type)是动态的,但"你是一个客户"
    这件事是静态的,所以这一层只声明角色框架,细节由 L2 填。
    """

    name = "L1_persona_customer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "你正在扮演一个金融营销陪练场景中的客户,与员工对话。具体的画像和顾虑会在"
            "下面的上下文里给出。你的最高准则:\n"
            "- 全程保持客户身份,绝不出戏\n"
            "- 真实精明客户的语气——可以质疑、犹豫、不耐烦、揪员工话里的漏洞\n"
            "- 不要帮员工想答案,你只是提出问题/质疑/反应"
        )


# ============================================================
# L3 核心指令层
# ============================================================

class CustomerInstructionLayer(PromptLayer):
    """L3 任务 + 决策树(优先级 + 示例)。"""

    name = "L3_instruction_customer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "## L3 任务:生成下一句客户追问/回应\n"
            "按以下优先级决定说什么(在心里走一遍,不要把过程输出):\n"
            "1. 员工话里有合规风险(承诺/保证/绝对化/包装成存款/合理避税等)"
            " → 优先尖锐追问该风险,逼员工把承诺具体化\n"
            "2. 否则若有未回应顾虑(下方 gap 列表) → 围绕第一个未回应顾虑发问,可带情绪\n"
            "3. 否则(全部已回应)→ 表示理解,自然推进到办理意向\n"
            "4. 任何情况下都要紧扣员工**这一轮具体说的话**,不能跑题\n\n"
            "## L3 决策示例(展示判断流程,你只输出最后的客户那句话)\n\n"
            "示例 A(员工踩合规雷):\n"
            "  员工说:'稳赚不赔,大公司绝对保证'\n"
            "  → 触发优先级 1 → 输出:'稳赚?那你敢写进合同保证给我看吗?'\n\n"
            "示例 B(员工答得普通,有 gap):\n"
            "  员工说:'这款产品需要每年缴费,请以合同为准'\n"
            "  gap = [liquidity_concern, procedure_question]\n"
            "  → 触发优先级 2 → 输出:'你光说以合同为准,合同里到底能不能提前取?扣多少钱?'\n\n"
            "示例 C(全覆盖,推进办理):\n"
            "  员工已覆盖所有 expected_intents\n"
            "  → 触发优先级 3 → 输出:'好,那我现在适合办吗?要带什么材料?'\n\n"
            "示例 D(紧扣员工具体话,避免跑题):\n"
            "  员工说:'我们这款有保单贷款应急'\n"
            "  → 不要泛泛问流动性 → 输出:'那贷款利息怎么算?比银行高不高?'"
        )


# ============================================================
# L2 上下文注入层(动态)
# ============================================================

def _format_history(messages: list[dict[str, Any]], limit: int = 6) -> str:
    if not messages:
        return "(对话刚开始)"
    role_map = {"ai_customer": "客户(你之前说的)", "employee": "员工"}
    lines = []
    for msg in messages[-limit:]:
        role = role_map.get(msg.get("role", ""), msg.get("role", ""))
        content = str(msg.get("content", "")).strip()
        if content:
            lines.append(f"- {role}: {content}")
    return "\n".join(lines) if lines else "(无)"


def _format_intents(labels: list[str]) -> str:
    if not labels:
        return "(无)"
    return "、".join(
        f"{label}({INTENT_LABEL_DESCRIPTIONS.get(label, '')})" for label in labels
    )


def _format_retrieval(items: list[dict[str, Any]] | None, limit: int = 2) -> str:
    if not items:
        return "(无)"
    lines = []
    for i, item in enumerate(items[:limit], 1):
        content = str(item.get("content", "")).strip().replace("\n", " ")
        if len(content) > 160:
            content = content[:160] + "…"
        if content:
            lines.append(f"{i}. {content}")
    return "\n".join(lines) if lines else "(无)"


class CustomerContextLayer(PromptLayer):
    """L2 客户上下文:只放真正每轮变化的内容(画像已被 SceneAnchorLayer 烤进静态层)。"""

    name = "L2_context_customer"
    is_dynamic = True

    def render(self, context: dict[str, Any]) -> str:
        messages = context.get("messages") or []
        employee_message = context.get("employee_message") or ""
        gap_intents = context.get("gap_intents") or []
        covered_intents = context.get("covered_intents") or []
        retrieval_items = context.get("retrieval_items") or []
        weakness_prompt = context.get("weakness_prompt") or ""

        sections = [
            f"## L2.1 最近几轮对话历史\n{_format_history(messages)}",
            f"## L2.2 员工刚刚说\n{employee_message}",
            "## L2.3 算法辅助分析(参考,但要看上下文综合判断)\n"
            f"- 你尚未被回应的顾虑(按重要性排序): {_format_intents(gap_intents)}\n"
            f"- 你已经被回应过的顾虑: {_format_intents(covered_intents)}",
            f"## L2.4 相关的标准客户话术(参考语气,严禁照抄)\n{_format_retrieval(retrieval_items)}",
        ]
        if weakness_prompt:
            sections.append(weakness_prompt)
        return "\n\n".join(sections)


# ============================================================
# Public builder factory
# ============================================================

def build_customer_builder(
    profile: dict[str, Any] | None = None,
    scene_id: str | None = None,
) -> LayeredPromptBuilder:
    """组装客户模拟的完整 5 层 builder。

    顺序(scene-aware,prefix-cache 友好):
      system: L1 persona(scene-agnostic 静态)
      user:   L3 instruction → L4 global → L4 customer → L5 format
              → **L2-Anchor scene 画像(静态,同 scene 共享)**
              → L2 context(动态,每轮变)

    若不传 profile/scene_id,SceneAnchorLayer 会渲染占位文本——退化为旧行为。
    """
    return LayeredPromptBuilder(
        system_layer=CustomerPersonaLayer(),
        user_layers=[
            CustomerInstructionLayer(),
            GlobalBoundaryLayer(),
            CustomerBoundaryLayer(),
            CustomerFormatLayer(),
            CustomerSceneAnchorLayer(profile, scene_id),  # 静态,锚定 scene
            CustomerContextLayer(),                         # 动态,放最后
        ],
    )


# Per-scene builder 缓存:每个 scene_id 一个独立 builder 实例,
# 各自的静态层(含 SceneAnchor)只渲染一次,跨调用复用。
_CUSTOMER_BUILDER_CACHE: dict[str, LayeredPromptBuilder] = {}


def get_customer_builder_for_scene(
    profile: dict[str, Any] | None,
    scene_id: str | None,
) -> LayeredPromptBuilder:
    """按 scene_id 取/造 builder(进程级 LRU,无淘汰)。

    同一 scene 多次调用复用同一 builder,SceneAnchorLayer 的 profile 字节
    完全一致 → DeepSeek prefix cache 跨调用命中。
    """
    cache_key = scene_id or "default"
    if cache_key not in _CUSTOMER_BUILDER_CACHE:
        _CUSTOMER_BUILDER_CACHE[cache_key] = build_customer_builder(profile, scene_id)
    return _CUSTOMER_BUILDER_CACHE[cache_key]
