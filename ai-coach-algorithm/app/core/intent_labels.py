from __future__ import annotations


INTENT_LABELS = [
    "rate_concern",
    "liquidity_concern",
    "safety_concern",
    "procedure_question",
    "rejection_or_hesitation",
    "compliance_sensitive",
]


INTENT_LABEL_DESCRIPTIONS = {
    "rate_concern": "利率、收益、同业比较、是否划算",
    "liquidity_concern": "提前支取、临时用钱、期限灵活性",
    "safety_concern": "本金安全、风险、亏损、保障",
    "procedure_question": "办理流程、材料、查询、下一步动作",
    "rejection_or_hesitation": "犹豫、拒绝、再考虑、和家人商量",
    "compliance_sensitive": "保证、承诺、最高收益、稳赚等合规敏感表达",
}


INTENT_KEYWORDS = {
    "rate_concern": ["利率", "收益", "高一点", "划算", "别的银行", "比较", "利息"],
    "liquidity_concern": ["急用", "随时", "提前取", "流动", "不方便", "短期", "期限", "活期"],
    "safety_concern": ["风险", "亏", "本金", "安全吗", "保障", "保本", "安全"],
    "procedure_question": ["怎么办", "办理", "需要什么", "流程", "材料", "查询", "身份证", "网点"],
    "rejection_or_hesitation": ["再看看", "考虑", "不用", "算了", "担心", "犹豫", "商量", "回去想"],
    "compliance_sensitive": ["保证", "最高", "稳赚", "承诺", "内部", "一定", "绝对"],
}

