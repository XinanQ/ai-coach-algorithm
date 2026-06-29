"""L5 输出格式层 — 强制结构化输出 schema。

每个场景定义自己的输出 schema。所有评分场景共用同一份 schema(对应
LLMScoreOutput Pydantic 模型);客户模拟场景是纯文本输出,不需要 JSON schema。
"""
from __future__ import annotations

import json
from typing import Any

from app.core.llm.prompts.base import PromptLayer


_SCORER_SCHEMA = {
    "dimension_scores": {
        "compliance": "0-100 整数,命中合规红线必须 ≤30;'请以合同为准/不确定/可能'等合规揭示加分",
        "objection_handling": "0-100,覆盖标准要点的程度",
        "logic_structure": "0-100,回答结构是否清晰(共情→解释→引导)",
        "empathy": "0-100,是否先认可顾虑、站在客户角度",
    },
    "weakness_tags": ["简短弱点标签,例如:合规风险、标准要点覆盖不足"],
    "missing_points": ["实际仍未覆盖的标准要点文本"],
    "risk_terms": ["命中的合规敏感词或表述"],
    "suggestion": "一句话改进建议,中文,<=80 字",
}


_SCORER_GOOD_EXAMPLE = {
    "dimension_scores": {
        "compliance": 85,
        "objection_handling": 70,
        "logic_structure": 72,
        "empathy": 65,
    },
    "weakness_tags": ["共情挖掘不足", "标准要点覆盖部分"],
    "missing_points": ["说明现金价值的变化规律", "提示退保前几年损失情况"],
    "risk_terms": [],
    "suggestion": "先认可客户对流动性的担忧,再补充现金价值的具体变化规律,并提示前期退保损失。"
}

_SCORER_BAD_EXAMPLE = {
    "dimension_scores": {
        "compliance": 10,
        "objection_handling": 30,
        "logic_structure": 35,
        "empathy": 20,
    },
    "weakness_tags": ["合规红线", "绝对化承诺", "包装成存款", "未做风险揭示"],
    "missing_points": ["分红存在不确定性", "以保险合同为准"],
    "risk_terms": ["稳赚不赔", "跟存款一样", "绝对保证"],
    "suggestion": "删除所有绝对化承诺,严禁将保险类比存款,围绕合同条款和保障责任进行规范说明。"
}


class ScorerFormatLayer(PromptLayer):
    """评分场景统一 schema(finish 和 reply 共用)。"""

    name = "L5_format_scorer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "## L5 输出格式(严格 JSON,不许多余文字)\n"
            "### Schema 描述\n"
            "```json\n"
            + json.dumps(_SCORER_SCHEMA, ensure_ascii=False, indent=2)
            + "\n```\n\n"
            "### 良好评分输出示例(中等水平员工回答的合理评分)\n"
            "```json\n"
            + json.dumps(_SCORER_GOOD_EXAMPLE, ensure_ascii=False, indent=2)
            + "\n```\n\n"
            "### 严重违规评分输出示例(踩到合规红线时的合理评分)\n"
            "```json\n"
            + json.dumps(_SCORER_BAD_EXAMPLE, ensure_ascii=False, indent=2)
            + "\n```\n\n"
            "### 格式校验清单(输出前自检)\n"
            "- [ ] dimension_scores 4 个键齐全且都是 0-100 整数?\n"
            "- [ ] compliance ≥85 时,weakness_tags 和 risk_terms 不能含合规相关条目?\n"
            "- [ ] suggestion 是一句话(≤80 字)?\n"
            "- [ ] 全文只有 JSON,没有任何 markdown 包裹、解释、前后缀?"
        )


class CustomerFormatLayer(PromptLayer):
    """客户模拟场景:纯文本输出,只规定形态约束。"""

    name = "L5_format_customer"
    is_dynamic = False

    def render(self, context: dict[str, Any]) -> str:
        return (
            "## L5 输出形态\n"
            "- 直接输出客户要说的那一句话,不带任何前缀('客户:'/'我说:')\n"
            "- 单次发言一到两句话,不超过 60 字\n"
            "- 中文口语化,不用书面语和过渡词\n\n"
            "## L5 输出风格示例(贴合精明客户的口吻)\n"
            "✓ 好的输出:\n"
            "  - '你光说以合同为准,合同里到底能不能提前取?扣多少钱?'\n"
            "  - '那贷款利息怎么算?比银行高不高?'\n"
            "  - '稳赚?那你敢写进合同里吗?写进去我立刻办。'\n"
            "  - '我再想想,这个事儿我得跟家里商量。'\n\n"
            "✗ 不好的输出:\n"
            "  - '那么,我想了解一下贷款的利息情况' (AI 腔)\n"
            "  - '好的,我明白了,谢谢您的解释' (太顺从)\n"
            "  - '作为客户,我比较关心流动性' (出戏,自报家门)\n"
            "  - '请问能否详细说明一下合同条款' (太书面)"
        )
