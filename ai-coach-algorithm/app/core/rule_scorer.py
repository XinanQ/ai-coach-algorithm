from __future__ import annotations

from typing import Any

from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.text_cleaner import clean_text


# Terms that signal good marketing practice (used as a weak fallback signal when
# no rubric coverage is available, e.g. the per-turn liveScore on reply).
GOOD_PRACTICE_TERMS = ["了解", "顾虑", "资金", "期限", "利率", "安全", "查询", "办理", "活期", "到期"]
# Global compliance red lines; merged with the scene criterion's own red lines.
HIGH_RISK_TERMS = ["稳赚", "保证最高", "承诺收益", "内部利率", "一定不会亏", "保本", "无风险", "锁定收益"]
# Negative patterns that indicate the following terms are in a negative context
NEGATIVE_PATTERNS = ["不", "没", "无", "别", "避免", "不能", "不要", "并非", "并没有", "不存在", "没有", "绝非", "绝非是", "不可以", "无法"]
# Empathy / customer-acknowledgement expressions.
EMPATHY_TERMS = ["理解", "了解", "明白", "顾虑", "担心", "为您", "帮您", "您的", "认可", "考虑到", "我懂"]
# Next-step / guidance expressions (also a logic-structure signal).
GUIDANCE_TERMS = ["查询", "办理", "下一步", "方案", "建议您", "可以为您", "安排", "预约"]


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
    - "不保本" → "保本" is in negative context
    - "绝对保本" → "保本" is NOT in negative context
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


def _score_compliance(value: str, red_lines: list[str]) -> tuple[int, list[str]]:
    """合规度：踩到任何合规红线都重罚。无红线命中给满分。

    修复：检测否定语境，避免"不保本"等正确表达被误判。
    """
    hits = sorted({term for term in red_lines if term and term in value})

    # Filter out hits that are in negative context
    actual_hits = []
    for term in hits:
        if not _is_in_negative_context(value, term):
            actual_hits.append(term)

    return _clamp(100 - len(actual_hits) * 40), actual_hits


def _score_objection(value: str, coverage: dict[str, Any] | None) -> int:
    """异议处理：核心看导师侧 must_point 覆盖率（答到了几个标准要点）。

    没有 coverage（如 reply 阶段的 liveScore）时降级到关键词粗估。
    """
    if coverage and coverage.get("items"):
        # Use more lenient scoring for coverage
        coverage_rate = float(coverage.get("coverage_rate", 0.0))
        # Boost the score: if coverage rate is 0.3+, give it more credit
        if coverage_rate >= 0.3:
            return _clamp(coverage_rate * 100 + 15)  # +15 bonus
        return _clamp(coverage_rate * 100)
    hits = [term for term in GOOD_PRACTICE_TERMS if term in value]
    return _clamp(40 + len(hits) * 8)


def _score_logic(value: str, coverage: dict[str, Any] | None, reference_items: list[dict[str, Any]] | None) -> int:
    """逻辑结构：标准要点覆盖率 + 检索语义贴合度（回答是否落在标准话术附近）。"""
    retrieval = float((reference_items or [{}])[0].get("score", 0.0)) if reference_items else 0.0
    retrieval = max(0.0, min(1.0, retrieval))
    if coverage and coverage.get("items"):
        cov = float(coverage.get("coverage_rate", 0.0))
        # Boost logic score when coverage is decent
        base_score = cov * 60 + retrieval * 40
        if cov >= 0.25:
            base_score += 10  # +10 bonus for decent coverage
        return _clamp(base_score)
    hits = [term for term in GOOD_PRACTICE_TERMS if term in value]
    return _clamp(45 + len(hits) * 8 + retrieval * 15)


def _score_empathy(value: str) -> int:
    """共情力：是否先认可顾虑、站在客户角度、给出引导。纯表达层信号。"""
    empathy_hits = [term for term in EMPATHY_TERMS if term in value]
    has_guidance = any(term in value for term in GUIDANCE_TERMS)
    # More lenient scoring
    base_score = 35 + len(empathy_hits) * 12 + (20 if has_guidance else 0)
    # Boost if answer has decent length (shows thoughtfulness)
    if len(value) >= 30:
        base_score += 5
    return _clamp(base_score)


def _build_suggestion(
    dimension_scores: dict[str, int],
    missing_texts: list[str],
    risk_hits: list[str],
) -> str:
    parts: list[str] = []
    if risk_hits:
        parts.append("避免使用“" + "、".join(risk_hits) + "”等合规敏感表述")
    if missing_texts:
        parts.append("补充以下标准要点：" + "；".join(missing_texts[:2]))
    # Call out the weakest non-compliance dimension when nothing more concrete fired.
    name_map = {"objection_handling": "异议处理", "logic_structure": "回答的逻辑结构", "empathy": "对客户顾虑的共情"}
    weak = [(k, v) for k, v in dimension_scores.items() if k in name_map and v < 60]
    if weak:
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
    """
    value = clean_text(answer)
    criterion = criterion or {}
    missing_points = missing_points or (coverage or {}).get("missing_texts") or []

    red_lines = sorted(set(HIGH_RISK_TERMS) | set(criterion.get("compliance_red_lines") or []))
    compliance, risk_hits = _score_compliance(value, red_lines)
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

    dimension_scores = [
        {"key": key, "name": name, "score": scores[key], "weight": weight}
        for key, name, weight in DIMENSION_DEFS
    ]

    weakness_tags: list[str] = []
    # More lenient thresholds for weakness tags
    if compliance < 80:  # Raised from 100
        weakness_tags.append("合规风险")
    if objection < 65 or missing_points:  # Raised from 60
        weakness_tags.append("标准要点覆盖不足")
    if logic < 55:  # Raised from 60
        weakness_tags.append("逻辑结构待加强")
    if empathy < 55:  # Raised from 60
        weakness_tags.append("需求挖掘与共情不足")

    return {
        "total_score": total,
        "dimension_scores": dimension_scores,
        "matched_terms": [term for term in GOOD_PRACTICE_TERMS if term in value],
        "risk_terms": risk_hits,
        "missing_points": missing_points,
        "weakness_tags": weakness_tags,
        "suggestion": _build_suggestion(scores, missing_points, risk_hits),
        "intent_understanding": analyze_customer_answer(answer),
        "method": "rule_scorer_v6_multi_dimension",
    }
