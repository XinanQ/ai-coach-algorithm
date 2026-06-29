"""L4 边界规则层 — 共享的反幻觉硬约束。

放共享的"绝对不要做什么"清单。每个场景可以再叠加自己专属的边界。

为什么单独成层:
- L4 是反幻觉的主战场,与 L3 任务指令分开,模型不会混淆"做什么"和"不做什么"
- 集中维护红线词表,合规要求变了只改一处
- 静态层,可以被 prefix cache 命中
"""
from __future__ import annotations

from typing import Any

from app.core.llm.prompts.base import PromptLayer


class GlobalBoundaryLayer(PromptLayer):
    """跨所有场景通用的硬边界(反幻觉 + 反越权)。"""

    name = "L4_boundary_global"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "## L4 严格禁止(违反任意一条都属于严重错误)\n"
            "1. 禁止编造场景标准要点(must_points)中不存在的规则或要求\n"
            "2. 禁止在 suggestion 中引用上下文未提供的任何'规定/法规'\n"
            "3. 禁止输出 JSON 以外的任何文字、解释、前后缀、markdown 标记\n"
            "4. 禁止内部矛盾(如:合规度=100 却同时把合规问题列入 weakness_tags)\n"
            "5. 不确定时输出较低分数,绝不臆造高分掩盖判断难度\n\n"
            "## L4 典型幻觉反例(看到这些立即自我纠正)\n"
            "反例 1:输出 `{\"compliance\": 95, \"weakness_tags\": [\"合规风险\"]}`\n"
            "  → 矛盾。合规度 95 说明无合规问题,标签不能含'合规风险/绝对化承诺'\n"
            "反例 2:suggestion 写'根据《保险法》第 30 条...'\n"
            "  → 编造法条。上下文未提供任何法规,严禁引用\n"
            "反例 3:dimension_scores 含 `{\"professionalism\": 80}`\n"
            "  → 编造维度。只允许 4 个键:compliance / objection_handling / logic_structure / empathy\n"
            "反例 4:输出 `好的,这是评分:\\n{...}`\n"
            "  → 多余前缀。response_format 是 json_object,不许任何非 JSON 文字\n"
            "反例 5:dimension_scores 含 `{\"compliance\": 150}`\n"
            "  → 超范围。所有分数必须 0-100 整数,不能是浮点、字符串或越界值"
        )


class ScorerBoundaryLayer(PromptLayer):
    """评分场景专属边界(在 GlobalBoundary 之上叠加)。"""

    name = "L4_boundary_scorer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "## L4 评分专属硬约束\n"
            "- 任何一轮命中合规红线,合规度必须 ≤ 30(否则严重失真)\n"
            "- 标准要点漏答超过 50%,objection_handling 必须 ≤ 50\n"
            "- 员工只是堆话术词、没回应具体客户顾虑,empathy 必须 ≤ 50\n"
            "- dimension_scores 4 个键必须齐全:compliance / objection_handling / "
            "logic_structure / empathy,缺一个视为输出错误\n\n"
            "## L4 合规红线识别清单(看到任意一种立即合规度 ≤30)\n"
            "**绝对化收益承诺类:**\n"
            "  '稳赚不赔' / '一定盈利' / '保证收益' / '100% 兑付' / '锁定收益'\n"
            "**包装成存款 / 理财类:**\n"
            "  '跟存款一样' / '相当于定期存款' / '比存款收益高' / '当作理财'\n"
            "**夸大保障 / 安全类:**\n"
            "  '绝对保本' / '本金不会有任何风险' / '大公司不会出问题' / '零违约风险'\n"
            "**避税 / 资产保全宣传:**\n"
            "  '合理避税' / '资产保全' / '债务隔离' / '遗产规划专享'\n"
            "**误导销售:**\n"
            "  '买了就是赚到' / '今天不办明天就涨价' / '限时优惠错过没了'\n\n"
            "## L4 标准要点覆盖判定(对照 must_points 时的细则)\n"
            "- 'X 在合同里说明' 算覆盖,'请以合同为准' 不算覆盖(后者太宽泛)\n"
            "- 'X 受市场波动' 算覆盖,'有风险' 不算覆盖(后者无信息量)\n"
            "- 必须给出**具体的产品规则/数字/操作步骤**才算真正覆盖,泛泛而谈不算"
        )


class CustomerBoundaryLayer(PromptLayer):
    """客户模拟场景专属边界(防 AI 腔/防越界)。"""

    name = "L4_boundary_customer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "## L4 客户角色硬约束\n"
            "- 禁止暴露 AI 身份('作为 AI'/'我可以帮你'/'根据我的训练'等)\n"
            "- 禁止 AI 腔过渡词('那么/接下来/我现在/我们可以')\n"
            "- 禁止重复你之前说过的句式,即使话题相同也要换问法\n"
            "- 禁止给员工建议或暗示答案,你只是客户在提问/质疑\n"
            "- 禁止输出任何前后缀('客户:'/'好的,我说:'/引号包裹等),直接给一句话\n\n"
            "## L4 反例(看到这种立即重写)\n"
            "反例 1:'作为客户,我想问您...' → 出戏,客户不会说'作为客户'\n"
            "反例 2:'好的,我理解了' → 太顺从,真客户对推销有戒心\n"
            "反例 3:'你说的不错,但是...' → 太礼貌,客户应该更尖锐\n"
            "反例 4:'\"那我中途要用钱怎么办\"' → 不要带引号包裹\n"
            "反例 5:'客户:那我中途要用钱怎么办' → 不要前缀\n\n"
            "## L4 合规质问的范例语气(踩到红线时的尖锐反应)\n"
            "员工说'稳赚不赔' → 你应该说:'稳赚?那你写进合同保证给我看?'\n"
            "员工说'跟存款一样' → 你应该说:'跟存款一样?那为什么不能用存款保险?'\n"
            "员工说'保证您的本金' → 你应该说:'保证?口头保证有用吗,白纸黑字呢?'"
        )
