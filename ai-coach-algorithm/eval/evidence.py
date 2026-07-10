"""Route-specific E2E evidence anchors derived from follow-up directions."""
from __future__ import annotations


def customer_evidence_from_direction(direction: object) -> list[str]:
    """Convert a desired customer behavior into retrievable business topics.

    A direction such as "客户可能反感" describes generated behavior, not text
    that should literally occur in the knowledge base. This function keeps only
    domain concepts that can reasonably ground the next customer turn.
    """
    value = str(direction or "").strip()
    if not value:
        return []

    anchors: list[str] = []

    def add(anchor: str) -> None:
        if anchor not in anchors:
            anchors.append(anchor)

    suitability_terms = ("风险偏好", "风险测评", "风险等级", "风险匹配", "适合性", "适当性", "资金期限")
    if any(term in value for term in suitability_terms):
        add("适当性")

    if any(term in value for term in ("承诺", "合规", "内部信息", "内部消息")):
        add("合规")
    if any(term in value for term in ("收益", "利率", "分红", "回报")):
        add("收益")
    if any(term in value for term in ("本金", "安全", "风险", "亏损", "波动")):
        add("风险")
    if any(term in value for term in ("赎回", "退保", "现金价值", "流动性", "到账")):
        add("流动性")
    if any(term in value for term in ("费用", "缴费", "费率")):
        add("费用")
    if any(term in value for term in ("办理", "材料", "渠道", "流程", "具体时间")):
        add("办理")
    if any(term in value for term in ("合同", "条款", "资料内容")):
        add("合同")
    if "保障" in value:
        add("保障")
    if any(term in value for term in ("产品", "具体方案", "其他产品")):
        add("产品")
    if any(term in value for term in ("异议", "反感", "销售压力", "邀约压力", "考虑", "商量")):
        add("异议")
    if any(term in value for term in ("专业术语", "信息重点")):
        add("清晰说明")

    # A purchase confirmation is grounded by next-step process material. Pure
    # agreement/decision carries no independent knowledge-evidence requirement.
    if "购买" in value and not anchors:
        add("办理")

    return anchors


def customer_evidence_after_each_turn(directions: list[object] | None) -> list[list[str]]:
    return [customer_evidence_from_direction(direction) for direction in directions or []]
