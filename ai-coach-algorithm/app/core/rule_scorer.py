from __future__ import annotations

from typing import Any

from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.text_cleaner import clean_text


# Terms that signal good marketing practice (used as a weak fallback signal when
# no rubric coverage is available, e.g. the per-turn liveScore on reply).
GOOD_PRACTICE_TERMS = ["了解", "顾虑", "资金", "期限", "利率", "安全", "查询", "办理", "活期", "到期"]
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
]
# Negative patterns that indicate the following terms are in a negative context
NEGATIVE_PATTERNS = ["不", "没", "无", "别", "避免", "不能", "不要", "并非", "并没有", "不存在", "没有", "绝非", "绝非是", "不可以", "无法"]
# Empathy / customer-acknowledgement expressions.
EMPATHY_TERMS = ["理解", "了解", "明白", "顾虑", "担心", "为您", "帮您", "您的", "认可", "考虑到", "我懂"]
# Next-step / guidance expressions (also a logic-structure signal).
GUIDANCE_TERMS = ["查询", "办理", "下一步", "方案", "建议您", "可以为您", "安排", "预约"]
# Positive compliance patterns - indicates proper risk disclosure and compliance boundaries
POSITIVE_COMPLIANCE_PATTERNS = [
    "以实际为准", "以合同为准", "以说明书为准", "请看合同", "请看条款", "按合同",
    "不承诺", "不确定", "可能有风险", "投资有风险", "过往不代表未来", "历史不代表未来",
    "根据监管要求", "监管规定", "合规要求", "不能承诺", "无法承诺",
    "风险自担", "盈亏自负", "本金可能亏损", "收益不确定", "不保本", "不保息",
]
# Excellent objection handling patterns - indicates addressing customer concerns properly
EXCELLENT_OBJECTION_PATTERNS = [
    "我理解您的", "我明白您的", "认可您的", "尊重您的", "理解您的顾虑", "考虑到您的",
    "我们可以", "为您提供", "为您设计", "为您准备", "帮您解决",
]
# Hard selling patterns - indicates pushy behavior
HARD_SELLING_PATTERNS = [
    "再想想就算了", "不买就没有了", "错过就没了", "很难得", "没机会", "抓紧", "赶紧",
    "施压", "逼您", "必须买", "一定要买",
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
        ]
    )

    return base_score, actual_hits, severe_violation


def _score_objection(value: str, coverage: dict[str, Any] | None) -> int:
    """Objection handling: core is must_point coverage rate (how many standard points covered).

    Without coverage (like reply stage liveScore), downgrade to keyword estimation.
    New: detect excellent objection handling patterns.
    """
    if coverage and coverage.get("items"):
        # Use more lenient scoring for coverage
        coverage_rate = float(coverage.get("coverage_rate", 0.0))
        # Boost the score: if coverage rate is 0.3+, give it more credit
        if coverage_rate >= 0.3:
            return _clamp(coverage_rate * 100 + 18)  # Moderate bonus
        return _clamp(coverage_rate * 100 + 5)
    hits = [term for term in GOOD_PRACTICE_TERMS if term in value]
    base_score = _clamp(40 + len(hits) * 8)

    # Check for excellent objection handling patterns
    excellent_hits = [p for p in EXCELLENT_OBJECTION_PATTERNS if p in value]
    if excellent_hits:
        # Moderate boost for excellent objection handling
        base_score = min(95, base_score + 30)

    return base_score


def _score_logic(value: str, coverage: dict[str, Any] | None, reference_items: list[dict[str, Any]] | None) -> int:
    """Logic structure: standard point coverage + retrieval semantic fit (whether answer aligns with standard scripts).

    New: detect compliance disclosure patterns to boost logic structure score.
    """
    retrieval = float((reference_items or [{}])[0].get("score", 0.0)) if reference_items else 0.0
    retrieval = max(0.0, min(1.0, retrieval))
    if coverage and coverage.get("items"):
        cov = float(coverage.get("coverage_rate", 0.0))
        # Boost logic score when coverage is decent
        base_score = cov * 60 + retrieval * 40 + 5  # Moderate base bonus
        if cov >= 0.25:
            base_score += 12  # Moderate bonus
        return _clamp(base_score)
    hits = [term for term in GOOD_PRACTICE_TERMS if term in value]
    base_score = _clamp(48 + len(hits) * 8 + retrieval * 18)  # Moderate adjustments

    # Check for positive compliance patterns in logic (proper risk disclosure)
    positive_hits = [p for p in POSITIVE_COMPLIANCE_PATTERNS if p in value]
    if positive_hits:
        base_score = min(95, base_score + 25)  # Moderate boost

    return base_score


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

    scores = {
        "compliance": compliance,
        "objection_handling": objection,
        "logic_structure": logic,
        "empathy": empathy,
    }
    total = _clamp(sum(scores[key] * weight for key, _, weight in DIMENSION_DEFS))

    # Hard cap for severe compliance violations - stricter limit
    if severe_violation:
        total = min(total, 20)  # Reduced from 30 to 20
        # Also cap compliance dimension
        scores["compliance"] = min(scores["compliance"], 10)  # Reduced from 20 to 10
        # Cap other dimensions too for severe violations
        scores["objection_handling"] = min(scores["objection_handling"], 30)
        scores["logic_structure"] = min(scores["logic_structure"], 30)
        scores["empathy"] = min(scores["empathy"], 30)

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
    if answer_len > 200:
        # Very long answer might be information overload
        # Check if it contains many numbers/technical terms without structure
        import re
        number_count = len(re.findall(r'\d+', value))
        if number_count > 10:
            # Likely information overload - penalize slightly
            total = min(total, 70)  # Cap at 70
            scores["logic_structure"] = min(scores["logic_structure"], 50)

    # Hard selling detection
    hard_selling_hits = [p for p in HARD_SELLING_PATTERNS if p in value]
    if hard_selling_hits and not any("不" in h or "没" in h for h in hard_selling_hits):
        total = min(total, 35)
        scores["objection_handling"] = min(scores["objection_handling"], 30)
        scores["empathy"] = min(scores["empathy"], 30)

    dimension_scores = [
        {"key": key, "name": name, "score": scores[key], "weight": weight}
        for key, name, weight in DIMENSION_DEFS
    ]

    # More granular weakness tags
    weakness_tags: list[str] = []

    # Compliance-related tags
    if severe_violation:
        weakness_tags.append("合规问题")
        weakness_tags.append("不当承诺")
    elif compliance < 80:
        weakness_tags.append("合规风险")

    if any("收益" in h for h in risk_hits):
        weakness_tags.append("收益说明不规范")
    if any("保本" in h or "无风险" in h for h in risk_hits):
        weakness_tags.append("风险揭示不足")

    # Coverage-related tags
    if objection < 65 or missing_points:
        if answer_len < 30:
            weakness_tags.append("信息提供不足")
            weakness_tags.append("产品说明缺失")
        else:
            weakness_tags.append("标准要点覆盖不足")

    # Logic-related tags
    if logic < 55:
        if answer_len > 200:
            weakness_tags.append("信息过载")
            weakness_tags.append("重点不突出")
        else:
            weakness_tags.append("逻辑结构待加强")

    # Empathy-related tags
    if empathy < 55:
        weakness_tags.append("需求确认不足")
        if answer_len < 30:
            weakness_tags.append("需求挖掘与共情不足")

    # Hard selling tags
    if hard_selling_hits and not any("不" in h or "没" in h for h in hard_selling_hits):
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
        "method": "rule_scorer_v7_multi_dimension_with_severe_violation_detection",
    }