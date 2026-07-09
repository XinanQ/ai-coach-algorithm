from __future__ import annotations

from typing import Any

from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.text_cleaner import clean_text


# Terms that signal good marketing practice (used as a weak fallback signal when
# no rubric coverage is available, e.g. the per-turn liveScore on reply).
GOOD_PRACTICE_TERMS = [
    "了解", "顾虑", "资金", "期限", "利率", "安全", "查询", "办理", "活期", "到期",
]
# Global compliance red lines; merged with the scene criterion's own red lines.
# Expanded version: includes severe compliance red lines, hitting them caps total score below 30
HIGH_RISK_TERMS = [
    "稳赚", "保证最高", "承诺收益", "内部利率", "一定不会亏", "保本", "无风险", "锁定收益",
    # New: severe promise-related
    "保证给您", "绝对保证", "一定给", "100%", "百分百",
    # New: contract-related violations
    "写进合同", "写进协议", "写入合同", "写入协议", "写进条款",
    # New: return guarantee
    "保证收益", "承诺收益", "收益保证", "必定收益",
    # New: principal guarantee
    "本金保证", "保证本金", "不会亏本", "绝对不会亏",
    # New: soft promise / suitability bypass patterns
    "肯定赚钱", "收益肯定", "基本都能拿到", "收益不会差", "内部消息", "大概率会涨",
    "不会亏", "本金不用担心", "不用测评", "不需要测评", "直接买就行",
    "没风险", "收益很稳定", "每年都能分红", "比存银行划算",
]
# Negative patterns that indicate the following terms are in a negative context
NEGATIVE_PATTERNS = ["不", "没", "无", "非", "别", "避免", "不能", "不要", "并非", "并没有", "不存在", "没有", "绝非", "绝非是", "不可以", "无法"]
# Empathy / customer-acknowledgement expressions.
EMPATHY_TERMS = ["理解", "了解", "明白", "顾虑", "担心", "担忧", "为您", "帮您", "您的", "认可", "考虑到", "我懂", "根据您的", "不急于", "家人商量"]
# Next-step / guidance expressions (also a logic-structure signal).
GUIDANCE_TERMS = ["查询", "办理", "下一步", "方案", "建议您", "可以为您", "安排", "预约", "设计", "推荐", "赎回", "规划", "资料", "现金流", "产品资料", "整理给您", "风险测评", "关键条款"]
# Positive compliance patterns - indicates proper risk disclosure and compliance boundaries
POSITIVE_COMPLIANCE_PATTERNS = [
    "以实际为准", "以合同为准", "以说明书为准", "请看合同", "请看条款", "按合同",
    "不承诺", "不确定", "可能有风险", "投资有风险", "过往不代表未来", "历史不代表未来",
    "根据监管要求", "监管规定", "合规要求", "不能承诺", "无法承诺",
    "风险自担", "盈亏自负", "本金可能亏损", "收益不确定", "不保本", "不保息",
    "风险测评", "产品说明书", "投保提示书", "以产品规则", "当时净值", "关键条款",
]
# Excellent objection handling patterns - indicates addressing customer concerns properly
EXCELLENT_OBJECTION_PATTERNS = [
    "我理解您的", "我明白您的", "认可您的", "尊重您的", "理解您的顾虑", "考虑到您的",
    "理解您对", "我理解您对", "我们可以", "为您提供", "为您设计", "为您准备", "帮您解决",
    "根据您的", "解决临时资金需求", "更灵活", "资金使用计划",
]
# Hard selling patterns - indicates pushy behavior
HARD_SELLING_PATTERNS = [
    "再想想就算了", "不买就没有了", "错过就没了", "很难得", "没机会", "抓紧", "赶紧",
    "施压", "逼您", "必须买", "一定要买", "别考虑了", "很抢手", "错过了就没了",
    "名额有限", "今天就签", "不来就错过", "必须来", "不用和家人商量", "别和家人商量",
    "明天可能就没有", "直接买就行",
]

LIQUIDITY_SOLUTION_TERMS = [
    "保单贷款", "临时资金", "资金使用计划", "更灵活", "交费方式", "赎回",
    "退保", "现金价值", "流动性", "资金规划",
]
FUND_RISK_LIQUIDITY_TERMS = [
    "非保本", "浮动收益", "投资有风险", "本金可能亏损", "市场波动", "赎回",
    "风险承受能力", "资金规划",
]
COMPLIANCE_BOUNDARY_TERMS = [
    "根据监管要求", "不能承诺", "无法承诺", "以实际", "收益不确定",
    "风险偏好", "合适的产品", "适合的产品", "不承诺收益", "不是固定收益",
]


# The four dimensions the front-end (联调文档 dimensionScores) expects, with the
# Chinese display name and the weight each contributes to the total score.
DIMENSION_DEFS = [
    ("compliance", "合规度", 0.30),
    ("objection_handling", "异议处理", 0.30),
    ("logic_structure", "逻辑结构", 0.20),
    ("empathy", "共情力", 0.20),
]


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> int:
    return int(max(low, min(high, round(value))))


def _hit_count(value: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term and term in value)


def _has_liquidity_solution(value: str) -> bool:
    return (
        _hit_count(value, LIQUIDITY_SOLUTION_TERMS) >= 2
        and any(term in value for term in ["理解", "担忧", "顾虑", "根据您的"])
    )


def _has_fund_risk_liquidity(value: str) -> bool:
    return (
        "赎回" in value
        and any(term in value for term in ["本金可能亏损", "市场波动"])
        and any(term in value for term in ["风险承受能力", "资金规划"])
    )


def _has_compliance_boundary(value: str) -> bool:
    return (
        any(term in value for term in ["根据监管要求", "监管规定", "合规要求"])
        and any(term in value for term in ["不能承诺", "无法承诺", "不承诺"])
        and any(term in value for term in ["风险偏好", "合适的产品", "适合的产品", "以实际"])
    )


def _is_information_overload(value: str) -> bool:
    import re

    answer_len = len(value)
    number_count = len(re.findall(r"\d+", value))
    separators = value.count("，") + value.count("、") + value.count(",") + value.count(";") + value.count("；")
    return answer_len >= 180 and (number_count >= 8 or separators >= 16)


def _is_technical_jargon_overload(value: str) -> bool:
    """Detect if answer uses too many technical terms without proper explanation.

    This catches cases where employee uses specialized financial terminology
    that average customers may not understand, even if the answer is not very long.
    """
    # Common financial jargon terms that are hard for average customers to understand
    JARGON_TERMS = [
        "公允价值", "摊余成本法", "估值", "夏普比率", "最大回撤", "波动率",
        "久期", "凸性", "利差", "信用利差", "流动性溢价", "风险溢价",
        "贝塔", "阿尔法", "波动率", "标准差", "协方差", "相关系数",
        "久期匹配", "免疫策略", "套利", "对冲", "衍生品", "期权",
        "期货", "掉期", "远期", "信用违约互换", "资产支持证券",
        "抵押贷款支持证券", "担保债务凭证", "杠杆率", "保证金",
    ]

    jargon_count = sum(1 for term in JARGON_TERMS if term in value)
    # If 3+ jargon terms appear in a relatively short answer (< 150 chars), it's jargon overload
    answer_len = len(value)
    return jargon_count >= 3 and answer_len < 150


def _has_missing_yield_explanation(value: str) -> bool:
    """Detect if answer misses yield/return explanation when it should have it.

    For marketing conversations, if the answer is relatively long and合规-compliant,
    but doesn't mention anything about yield/return, it's a weakness.
    """
    # Yield/return related terms
    YIELD_TERMS = [
        "收益", "利率", "回报", "分红", "年化", "收益率", "业绩",
        "利息", "赚", "增长", "波动", "净值", "表现",
    ]
    answer_len = len(value)
    has_yield = any(term in value for term in YIELD_TERMS)
    if answer_len < 40 or has_yield:
        return False

    product_context_terms = [
        "保险产品", "理财产品", "基金", "产品", "投保单", "缴费", "保费",
        "办理", "购买", "定期", "存款",
    ]
    exempt_focus_terms = [
        "邀约", "邀请", "时间安排", "哪天", "家人商量", "和家人",
        "费用", "退保", "赎回", "到账", "现金流", "产品资料", "风险提示",
        "合同条款", "关键条款",
    ]
    has_product_context = any(term in value for term in product_context_terms)
    is_non_yield_focus = any(term in value for term in exempt_focus_terms)
    return has_product_context and not is_non_yield_focus


def _has_missing_guidance(value: str, compliance_score: float) -> bool:
    """Detect if answer is compliant but lacks clear next-step guidance.

    This catches cases where employee explains risks properly but doesn't guide
    the customer toward any action or next step.
    """
    # Guidance terms
    GUIDANCE_TERMS = [
        "办理", "下一步", "方案", "建议您", "可以为您", "安排", "预约",
        "设计", "推荐", "赎回", "规划", "资料", "产品资料", "整理给您",
        "风险测评", "购买", "联系", "随时联系", "确认", "决定", "邀请",
        "方便", "时间安排", "来网点", "阅读", "仔细阅读",
    ]
    has_guidance = any(term in value for term in GUIDANCE_TERMS)
    # If answer is compliant (>= 65) but has no guidance and is reasonably long
    answer_len = len(value)
    return compliance_score >= 65 and answer_len >= 40 and not has_guidance


def _has_missing_action_guidance(value: str, compliance_score: float) -> bool:
    """Detect compliant information-only answers with no practical next step."""
    if compliance_score < 65 or len(value) < 40:
        return False
    action_terms = [
        "办理", "购买", "测评", "预约", "联系", "下一步", "安排", "确认", "推荐", "方案",
        "选择", "赎回", "提供资料", "整理给您", "来网点", "手机银行", "根据您的",
    ]
    info_only_terms = ["阅读", "仔细阅读", "说明书", "合同", "条款", "以实际运作为准", "不承诺保本", "投资有风险"]
    has_info_only = any(term in value for term in info_only_terms)
    has_action = any(term in value for term in action_terms)
    return has_info_only and not has_action


def _has_empathy_only_without_product(value: str) -> bool:
    """Detect empathy-only answers that do not provide product/risk content."""
    empathy_hits = _hit_count(value, EMPATHY_TERMS)
    product_core_terms = [
        "产品", "保险", "基金", "理财", "收益", "利率", "分红", "年化",
        "风险", "不保本", "亏损", "波动", "费用", "退保", "赎回",
        "合同", "条款", "说明书", "测评", "办理", "购买", "资料",
    ]
    has_core_content = any(term in value for term in product_core_terms)
    return len(value) >= 35 and empathy_hits >= 2 and not has_core_content


def _has_procedure_only_without_core(value: str) -> bool:
    """Detect process-only answers that skip risk and yield explanation."""
    procedure_terms = ["办理", "身份证", "银行卡", "投保单", "缴费", "流程", "30分钟", "今天方便"]
    risk_terms = ["不保本", "不保息", "投资有风险", "本金可能亏损", "波动", "退保", "损失", "合同条款", "说明书", "风险提示", "风险揭示"]
    yield_terms = ["收益", "利率", "回报", "分红", "年化", "净值", "业绩"]
    procedure_hits = _hit_count(value, procedure_terms)
    has_risk_or_yield = any(term in value for term in [*risk_terms, *yield_terms])
    has_suitability_context = any(term in value for term in ["产品说明书", "投保提示书", "关键条款"])
    return procedure_hits >= 3 and not has_risk_or_yield and not has_suitability_context


def _business_quality_profile(value: str) -> dict[str, bool | int]:
    """Summarize positive business signals in the full finish answer.

    Must-point coverage can be sparse when retrieval anchors do not match the
    exact wording of an otherwise good employee answer. This profile gives the
    rule scorer a transparent, domain-level calibration layer without weakening
    compliance red-line caps.
    """
    risk_terms = [
        "风险", "不保本", "不保息", "收益不确定", "不确定", "投资需谨慎", "投资有风险",
        "过往业绩不代表未来", "历史不代表未来", "本金可能亏损", "市场波动", "净值",
        "退保会有损失", "现金价值", "亏损",
    ]
    yield_terms = [
        "收益", "利率", "分红", "年化", "回报", "以实际", "实际运作", "实际为准",
        "以系统公示为准", "以说明书为准", "以产品说明书为准", "不保证",
    ]
    suitability_terms = [
        "风险测评", "风险承受能力", "风险偏好", "投资经验", "资金规划", "资金使用计划",
        "投资期限", "持有期限", "根据自身情况", "根据您的情况", "根据您的风险",
        "适合", "匹配", "需求", "确认", "了解",
    ]
    empathy_terms = [
        "理解", "明白", "尊重", "不急", "谨慎", "担忧", "顾虑", "商量", "家人",
        "认可", "考虑", "根据您的",
    ]
    guidance_terms = [
        "建议", "可以", "办理", "购买", "赎回", "阅读", "仔细阅读", "资料", "整理",
        "提供", "联系", "下一步", "流程", "材料", "身份证", "银行卡", "测评",
        "选择", "考虑", "推荐", "方案", "确认后",
    ]
    product_terms = [
        "产品", "基金", "理财", "保险", "保障", "合同", "条款", "说明书", "净值化",
        "债券", "货币基金", "短期理财", "底层资产", "费用", "管理费", "托管费",
        "认购费", "赎回", "缴费", "保单贷款",
    ]
    procedure_terms = ["办理", "流程", "材料", "身份证", "银行卡", "渠道", "手机银行", "网点", "投保单", "缴费"]
    respect_terms = ["尊重", "不急", "家人商量", "和家人", "资料", "整理给您", "供您参考", "根据您的时间", "哪天方便"]

    profile: dict[str, bool | int] = {
        "risk": any(term in value for term in risk_terms),
        "yield": any(term in value for term in yield_terms),
        "suitability": any(term in value for term in suitability_terms),
        "empathy": any(term in value for term in empathy_terms),
        "guidance": any(term in value for term in guidance_terms),
        "product": any(term in value for term in product_terms),
        "procedure": any(term in value for term in procedure_terms),
        "respect": any(term in value for term in respect_terms),
    }
    profile["signal_count"] = sum(1 for value_hit in profile.values() if value_hit is True)
    profile["phone_invitation"] = (
        any(term in value for term in ["邀请", "来网点", "了解一下", "哪天方便", "时间安排", "明天下午"])
        and any(term in value for term in ["方便", "时间", "安排", "邀约", "邀请"])
    )
    profile["direct_recommend_refusal"] = (
        any(term in value for term in ["直接推荐", "直接推荐可能不适合", "不太懂这些产品"])
        and bool(profile["suitability"])
        and bool(profile["risk"])
    )
    profile["customer_respect"] = bool(profile["empathy"]) and bool(profile["respect"])
    profile["fund_differentiation_only"] = (
        any(term in value for term in ["基金和理财不同", "基金是净值化", "每天的收益和本金都随市场波动"])
        and not bool(profile["empathy"])
        and not bool(profile["procedure"])
    )
    return profile


def _is_in_negative_context(text: str, term: str, window_size: int = 10) -> bool:
    """Check if a term appears in a negative context.

    A term is considered in negative context if:
    1. A negative pattern (不/没/无/别/避免) appears before it within window_size characters
    2. The negative pattern is not part of the term itself

    Examples:
    - "不保本" -> "保本" is in negative context
    - "绝对保本" -> "保本" is NOT in negative context
    """
    # Find all occurrences of the term in the text
    index = 0
    while True:
        pos = text.find(term, index)
        if pos == -1:
            break

        # Check for negative patterns before the term
        start = max(0, pos - window_size)
        before = text[start:pos]

        # Check if any negative pattern appears (but not as part of the term)
        for neg in NEGATIVE_PATTERNS:
            # Make sure the negative pattern is not part of the term
            if neg in before and neg not in term:
                # Additional check: ensure there's text between neg and term (not adjacent to term in a way that makes them one word)
                neg_pos = before.rfind(neg)
                if neg_pos != -1:
                    # There should be some content between neg and term, or neg should be standalone
                    after_neg = before[neg_pos + len(neg):]
                    # If there's content after neg or neg is at the very end of the window, it's negative
                    return True

        index = pos + 1  # Move to next position to find overlapping matches

    return False


def _is_customer_contract_request_context(text: str, term: str) -> bool:
    """Avoid treating a customer's contract request as the employee's promise."""
    contract_terms = {"写进合同", "写进协议", "写入合同", "写入协议", "写进条款"}
    if term not in contract_terms:
        return False

    pos = text.find(term)
    if pos == -1:
        return False
    before = text[max(0, pos - 16):pos]
    after = text[pos:pos + 80]
    request_markers = ["希望", "要求", "想", "能不能", "客户"]
    boundary_markers = ["以保险条款为准", "以条款为准", "以合同为准", "收益部分取决", "收益不确定", "产品说明书", "具体条款"]
    return any(marker in before for marker in request_markers) and any(marker in after for marker in boundary_markers)


def _score_compliance(value: str, red_lines: list[str]) -> tuple[int, list[str], bool]:
    """Compliance: hitting any red line gets heavy penalty. No red line hit gets full score.

    Fix: detect negative context to avoid false positives like "不保本".
    New: return severe_violation flag for subsequent hard cap.

    Args:
        value: employee answer text
        red_lines: compliance red line terms

    Returns:
        (compliance score, hit red line terms, is severe violation)
    """
    hits = sorted({term for term in red_lines if term and term in value})

    # Filter out hits that are in negative context
    actual_hits = []
    for term in hits:
        if _is_customer_contract_request_context(value, term):
            continue
        if not _is_in_negative_context(value, term):
            actual_hits.append(term)

    base_score = _clamp(100 - len(actual_hits) * 40)

    # Check for positive compliance patterns (good risk disclosure)
    positive_hits = [p for p in POSITIVE_COMPLIANCE_PATTERNS if p in value]
    if positive_hits and not actual_hits:
        # Has compliance disclosure but no violation, give extra points
        base_score = min(95, base_score + 10)

    # Severe violation: any hit on contract-related or absolute promise terms
    severe_violation = any(
        term in actual_hits for term in [
            "保证给您", "绝对保证", "一定给", "写进合同", "写进协议",
            "写入合同", "写入协议", "保证收益", "承诺收益",
            "肯定赚钱", "收益肯定", "基本都能拿到", "内部消息", "大概率会涨",
            "不会亏", "本金不用担心", "没风险", "收益很稳定", "每年都能分红",
        ]
    )

    return base_score, actual_hits, severe_violation


def detect_compliance_violation(
    answer: str,
    criterion: dict[str, Any] | None = None,
) -> tuple[list[str], bool]:
    """Deterministic red-line check, exposed for cross-validating LLM scoring.

    Runs the same negative-context-aware detection as `_score_compliance` so
    "不保本" style disclaimers do not false-positive. Returns
    (hit red-line terms, is severe violation).
    """
    value = clean_text(answer)
    red_lines = sorted(set(HIGH_RISK_TERMS) | set((criterion or {}).get("compliance_red_lines") or []))
    _, risk_hits, severe_violation = _score_compliance(value, red_lines)
    return risk_hits, severe_violation


def _score_objection(value: str, coverage: dict[str, Any] | None) -> int:
    """Objection handling: core is must_point coverage rate (how many standard points covered).

    Without coverage (like reply stage liveScore), downgrade to keyword estimation.
    New: detect excellent objection handling patterns.
    """
    hits = [term for term in GOOD_PRACTICE_TERMS if term in value]
    base_score = _clamp(40 + len(hits) * 8)

    excellent_hits = [p for p in EXCELLENT_OBJECTION_PATTERNS if p in value]
    if excellent_hits:
        base_score = min(95, base_score + 30)
    if _has_liquidity_solution(value):
        base_score = max(base_score, 88)
    if _has_fund_risk_liquidity(value):
        base_score = max(base_score, 78)
    if _has_compliance_boundary(value):
        base_score = max(base_score, 76)

    strong_objection_signal = bool(excellent_hits) or _has_liquidity_solution(value) or _has_fund_risk_liquidity(value) or _has_compliance_boundary(value)

    if coverage and coverage.get("items"):
        # Use more lenient scoring for coverage
        coverage_rate = float(coverage.get("coverage_rate", 0.0))
        # Boost the score: if coverage rate is 0.3+, give it more credit
        if coverage_rate >= 0.3:
            coverage_score = _clamp(coverage_rate * 100 + 18)
        else:
            coverage_score = _clamp(coverage_rate * 100 + 5)
        return max(coverage_score, base_score) if strong_objection_signal else coverage_score

    return base_score


def _score_logic(value: str, coverage: dict[str, Any] | None, reference_items: list[dict[str, Any]] | None) -> int:
    """Logic structure: standard point coverage + retrieval semantic fit (whether answer aligns with standard scripts).

    New: detect compliance disclosure patterns to boost logic structure score.
    """
    retrieval = float((reference_items or [{}])[0].get("score", 0.0)) if reference_items else 0.0
    retrieval = max(0.0, min(1.0, retrieval))
    signal_count = len([term for term in GOOD_PRACTICE_TERMS + GUIDANCE_TERMS if term in value])
    fallback_score = _clamp(40 + min(signal_count, 6) * 7 + retrieval * 12)

    positive_hits = [p for p in POSITIVE_COMPLIANCE_PATTERNS if p in value]
    if positive_hits:
        fallback_score = min(95, fallback_score + 18)
    if _has_liquidity_solution(value):
        fallback_score = max(fallback_score, 82)
    if _has_fund_risk_liquidity(value):
        fallback_score = max(fallback_score, 82)
    if _has_compliance_boundary(value):
        fallback_score = max(fallback_score, 84)

    strong_logic_signal = _has_liquidity_solution(value) or _has_fund_risk_liquidity(value) or _has_compliance_boundary(value)

    if coverage and coverage.get("items"):
        cov = float(coverage.get("coverage_rate", 0.0))
        # Boost logic score when coverage is decent
        base_score = cov * 60 + retrieval * 40 + 5  # Moderate base bonus
        if cov >= 0.25:
            base_score += 12  # Moderate bonus
        return max(_clamp(base_score), fallback_score) if strong_logic_signal else _clamp(base_score)

    return fallback_score


def _score_empathy(value: str) -> int:
    """Empathy: whether acknowledging concerns, standing from customer perspective, giving guidance. Pure expression-level signals."""
    empathy_hits = [term for term in EMPATHY_TERMS if term in value]
    has_guidance = any(term in value for term in GUIDANCE_TERMS)
    # Moderate scoring adjustments
    base_score = 37 + len(empathy_hits) * 13 + (22 if has_guidance else 0)
    # Boost if answer has decent length (shows thoughtfulness)
    if len(value) >= 30:
        base_score += 6
    # Small boost for "为您" patterns (customer-centric)
    if "为您" in value or "帮您" in value:
        base_score += 8
    return _clamp(base_score)


def _build_suggestion(
    dimension_scores: dict[str, int],
    missing_texts: list[str],
    risk_hits: list[str],
    severe_violation: bool = False,
) -> str:
    parts: list[str] = []
    if severe_violation:
        parts.append("严重违规：禁止承诺收益、保证保本或将收益写进合同")
    elif risk_hits:
        parts.append("避免使用「" + "」、「".join(risk_hits) + "」等合规敏感表述")
    if missing_texts:
        parts.append("补充以下标准要点：" + "；".join(missing_texts[:2]))
    # Call out the weakest non-compliance dimension when nothing more concrete fired.
    name_map = {"objection_handling": "异议处理", "logic_structure": "回答的逻辑结构", "empathy": "对客户顾虑的共情"}
    weak = [(k, v) for k, v in dimension_scores.items() if k in name_map and v < 60]
    if weak and not severe_violation:
        worst = min(weak, key=lambda kv: kv[1])
        parts.append("加强" + name_map[worst[0]])
    if not parts:
        return "回答整体完整、合规，可继续保持，并在成交引导上更主动。"
    return "建议：" + "；".join(parts) + "。"


def score_employee_answer(
    answer: str,
    reference_items: list[dict[str, Any]] | None = None,
    missing_points: list[str] | None = None,
    criterion: dict[str, Any] | None = None,
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score an employee answer on four dimensions grounded in the tutor side.

    - With a full rubric (`criterion` + `coverage`, the finish path): objection
      handling and logic structure are driven by must_point coverage, compliance
      by the scene's red lines. This is the real scoring.
    - Without them (the reply path, for a per-turn liveScore): every dimension
      degrades gracefully to keyword signals, so a rough live score still works.

    New:
    - Information insufficiency detection: penalty for too short answers
    - Information overload detection: identify overly long, information-stuffed answers
    - Hard selling detection: detect pushy, aggressive behaviors
    - Hard cap: severe compliance violations directly cap total score below 30
    - More granular weakness tags: compliance issues, improper promises, insufficient risk disclosure, etc.
    """
    value = clean_text(answer)
    criterion = criterion or {}
    missing_points = missing_points or (coverage or {}).get("missing_texts") or []

    red_lines = sorted(set(HIGH_RISK_TERMS) | set(criterion.get("compliance_red_lines") or []))
    compliance, risk_hits, severe_violation = _score_compliance(value, red_lines)
    objection = _score_objection(value, coverage)
    logic = _score_logic(value, coverage, reference_items)
    empathy = _score_empathy(value)
    liquidity_solution = _has_liquidity_solution(value)
    fund_risk_liquidity = _has_fund_risk_liquidity(value)
    compliance_boundary = _has_compliance_boundary(value)
    high_quality_answer = liquidity_solution or fund_risk_liquidity or compliance_boundary
    information_overload = _is_information_overload(value)
    jargon_overload = _is_technical_jargon_overload(value)
    hard_selling_hits = [p for p in HARD_SELLING_PATTERNS if p in value]
    # Enhanced suitability bypass detection: includes direct bypass AND low-risk/high-risk mismatch
    suitability_bypass = (
        any(term in value for term in ["不用测评", "不需要测评", "直接买就行"]) or
        # Detect low-risk customer recommended high-risk products
        (any(term in value for term in ["低风险", "保守型", "稳健型"]) and
         any(term in value for term in ["风险等级R4", "R4", "R5", "高风险", "风险较高"]))
    )
    coverage_rate = float((coverage or {}).get("coverage_rate", 0.0) or 0.0)
    unsupported_yield_projection = (
        any(term in value for term in ["历史年化收益", "年化收益率"])
        and not any(term in value for term in ["历史不代表未来", "历史收益不代表未来", "过往不代表未来", "以产品说明书为准", "以说明书为准", "以实际", "只是参考", "实际收益", "实际运作", "实际为准"])
    )
    empathy_only_without_product = _has_empathy_only_without_product(value)
    procedure_only_without_core = _has_procedure_only_without_core(value)
    business_profile = _business_quality_profile(value)
    signal_count = int(business_profile.get("signal_count", 0))
    high_quality_answer = high_quality_answer or signal_count >= 4 or bool(
        business_profile.get("direct_recommend_refusal") or business_profile.get("customer_respect")
    )
    corrected_compliance = (
        severe_violation
        and any(term in value for term in ["抱歉", "刚才表达不准确", "表达不准确", "刚才说得不准确"])
        and any(term in value for term in ["不保本", "不保息", "收益不确定", "投资有风险", "风险承受能力"])
    )

    if liquidity_solution:
        objection = max(objection, 88)
        logic = max(logic, 82)
        empathy = max(empathy, 76)
    if fund_risk_liquidity:
        compliance = max(compliance, 95)
        objection = max(objection, 78)
        logic = max(logic, 82)
        empathy = max(empathy, 50)
    if compliance_boundary:
        compliance = max(compliance, 95)
        objection = max(objection, 76)
        logic = max(logic, 84)
        empathy = max(empathy, 56)
    if corrected_compliance:
        compliance = max(compliance, 60)
        objection = max(objection, 50)
        logic = max(logic, 55)
    if not severe_violation:
        if business_profile.get("risk") and business_profile.get("product"):
            objection = max(objection, 50)
            logic = max(logic, 54)
        if business_profile.get("suitability"):
            objection = max(objection, 54)
            logic = max(logic, 56)
        if business_profile.get("guidance"):
            logic = max(logic, 60)
        if business_profile.get("empathy"):
            empathy = max(empathy, 62)
        if business_profile.get("customer_respect"):
            objection = max(objection, 70)
            empathy = max(empathy, 82)
        if business_profile.get("direct_recommend_refusal"):
            objection = max(objection, 76)
            logic = max(logic, 72)
            empathy = max(empathy, 82)
        if business_profile.get("phone_invitation"):
            objection = max(objection, 62)
            logic = max(logic, 62)
            empathy = max(empathy, 68)
        if signal_count >= 5:
            objection = max(objection, min(74, 40 + signal_count * 4))
            logic = max(logic, min(76, 42 + signal_count * 4))
        elif signal_count >= 4:
            objection = max(objection, 56)
            logic = max(logic, 58)
        if compliance >= 95 and objection <= 5 and len(value) >= 40:
            # Coverage can be zero when the answer is valid but phrased far from
            # the retrieved must-point anchors. Keep it in a modest band rather
            # than treating it like an empty answer.
            objection = max(objection, 40)
            logic = max(logic, 45)

    scores = {
        "compliance": compliance,
        "objection_handling": objection,
        "logic_structure": logic,
        "empathy": empathy,
    }
    total = _clamp(sum(scores[key] * weight for key, _, weight in DIMENSION_DEFS))

    if liquidity_solution:
        total = min(total, 92)
    if fund_risk_liquidity:
        total = min(total, 88)
    if compliance_boundary:
        total = min(total, 90)
    if coverage and coverage.get("items") and coverage_rate <= 0 and missing_points and not high_quality_answer:
        total = min(total, 55)
    if business_profile.get("yield") and business_profile.get("product") and not business_profile.get("procedure"):
        total = max(total, 50)
    if business_profile.get("yield") and business_profile.get("risk") and compliance >= 80:
        total = max(total, 55)
    if business_profile.get("fund_differentiation_only"):
        total = min(total, 65)
    if unsupported_yield_projection:
        total = min(total, 45)

    # Hard cap for severe compliance violations - stricter limit
    if severe_violation and not corrected_compliance:
        total = min(total, 20)  # Reduced from 30 to 20
        # Also cap compliance dimension
        scores["compliance"] = min(scores["compliance"], 10)  # Reduced from 20 to 10
        # Cap other dimensions too for severe violations
        scores["objection_handling"] = min(scores["objection_handling"], 30)
        scores["logic_structure"] = min(scores["logic_structure"], 30)
        scores["empathy"] = min(scores["empathy"], 30)
    elif corrected_compliance:
        total = min(max(total, 40), 55)

    # Information insufficiency penalty: very short answers get lower scores
    answer_len = len(value)
    if answer_len < 15:
        # Almost no substantive content
        total = min(total, 35)
        scores["logic_structure"] = min(scores["logic_structure"], 30)
    elif answer_len < 30:
        # Minimal content
        total = min(total, 45)
        scores["logic_structure"] = min(scores["logic_structure"], 40)

    # Information overload detection
    if information_overload:
        total = min(total, 65)
        scores["logic_structure"] = min(scores["logic_structure"], 50)
        scores["empathy"] = min(scores["empathy"], 55)
    # Technical jargon overload detection (even for shorter answers)
    elif jargon_overload:
        total = min(total, 60)
        scores["logic_structure"] = min(scores["logic_structure"], 45)
        scores["empathy"] = min(scores["empathy"], 50)

    # Hard selling detection
    if hard_selling_hits:
        total = min(total, 35)
        scores["objection_handling"] = min(scores["objection_handling"], 30)
        scores["empathy"] = min(scores["empathy"], 30)
    if suitability_bypass:
        total = min(total, 45)
        scores["compliance"] = min(scores["compliance"], 55)
        scores["logic_structure"] = min(scores["logic_structure"], 45)
    if empathy_only_without_product:
        total = min(total, 60)
        scores["logic_structure"] = min(scores["logic_structure"], 45)
    if procedure_only_without_core:
        total = min(total, 60)
        scores["logic_structure"] = min(scores["logic_structure"], 45)

    dimension_scores = [
        {"key": key, "name": name, "score": scores[key], "weight": weight}
        for key, name, weight in DIMENSION_DEFS
    ]

    # More granular weakness tags
    weakness_tags: list[str] = []

    # Compliance-related tags
    if severe_violation and not corrected_compliance:
        weakness_tags.append("合规问题")
        weakness_tags.append("不当承诺")
    elif compliance < 80:
        weakness_tags.append("合规风险")

    if any("收益" in h for h in risk_hits):
        weakness_tags.append("收益说明不规范")
    if unsupported_yield_projection:
        weakness_tags.append("收益说明不规范")
    if any("保本" in h or "无风险" in h for h in risk_hits):
        weakness_tags.append("风险揭示不足")
    if any("不会亏" in h or "本金不用担心" in h or "没风险" in h for h in risk_hits):
        weakness_tags.append("风险揭示不足")
    if suitability_bypass:
        weakness_tags.append("适当性管理不足")
        weakness_tags.append("风险揭示不足")
        weakness_tags.append("合规问题")  # Low-risk/high-risk mismatch is a compliance violation

    # Coverage-related tags
    if objection < 65 or (missing_points and not high_quality_answer):
        if answer_len < 30:
            weakness_tags.append("信息提供不足")
            weakness_tags.append("产品说明缺失")
        elif total < 65:
            weakness_tags.append("标准要点覆盖不足")

    # Logic-related tags
    if information_overload or jargon_overload:
        weakness_tags.append("信息过载")
        weakness_tags.append("重点不突出")
    elif logic < 55 and total < 65:
        weakness_tags.append("逻辑结构待加强")

    # Yield explanation missing
    if _has_missing_yield_explanation(value):
        weakness_tags.append("收益说明缺失")

    if empathy_only_without_product:
        weakness_tags.append("产品说明缺失")
        weakness_tags.append("行动引导不足")
    if procedure_only_without_core:
        weakness_tags.append("风险揭示不足")
        weakness_tags.append("收益说明缺失")

    # Guidance missing for compliant answers
    if _has_missing_guidance(value, compliance) or _has_missing_action_guidance(value, compliance):
        weakness_tags.append("成交引导不足")

    # Empathy-related tags
    if empathy < 55 and total < 65:
        weakness_tags.append("需求确认不足")
        if answer_len < 30:
            weakness_tags.append("需求挖掘与共情不足")

    # Hard selling tags
    if hard_selling_hits:
        weakness_tags.append("异议处理不当")
        weakness_tags.append("客户关系不佳")
        weakness_tags.append("强推销")

    # Procedure missing
    if coverage and coverage.get("missing_texts"):
        missing_str = "".join(coverage["missing_texts"])
        if "办理" in missing_str or "流程" in missing_str or "手续" in missing_str:
            weakness_tags.append("办理流程缺失")
            weakness_tags.append("行动引导不足")

    # Remove duplicates while preserving order
    weakness_tags = list(dict.fromkeys(weakness_tags))

    return {
        "total_score": total,
        "dimension_scores": dimension_scores,
        "matched_terms": [term for term in GOOD_PRACTICE_TERMS if term in value],
        "risk_terms": risk_hits,
        "missing_points": missing_points,
        "weakness_tags": weakness_tags,
        "suggestion": _build_suggestion(scores, missing_points, risk_hits, severe_violation),
        "intent_understanding": analyze_customer_answer(answer),
        "method": "rule_scorer_v8_business_signal_calibrated",
    }
