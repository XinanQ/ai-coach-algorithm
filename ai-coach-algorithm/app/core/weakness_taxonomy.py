"""Canonical weakness-tag taxonomy shared by scoring and evaluation."""
from __future__ import annotations

import re
from collections.abc import Iterable


CANONICAL_WEAKNESS_TAGS = (
    "合规问题",
    "不当承诺",
    "风险揭示不足",
    "收益说明不规范",
    "收益说明缺失",
    "产品说明缺失",
    "需求确认不足",
    "适当性管理不足",
    "行动引导不足",
    "信息提供不足",
    "信息过载",
    "重点不突出",
    "逻辑结构不足",
    "共情不足",
    "标准要点覆盖不足",
    "办理流程缺失",
    "异议处理不当",
    "客户关系不佳",
    "强推销",
)


_ALIASES = {
    "合规红线": "合规问题",
    "合规风险": "合规问题",
    "合规揭示不足": "合规问题",
    "绝对化承诺": "不当承诺",
    "收益承诺": "不当承诺",
    "保本承诺": "不当承诺",
    "保证收益": "不当承诺",
    "未做风险揭示": "风险揭示不足",
    "风险说明缺失": "风险揭示不足",
    "未说明风险": "风险揭示不足",
    "收益表达不规范": "收益说明不规范",
    "收益说明不完整": "收益说明缺失",
    "产品介绍缺失": "产品说明缺失",
    "需求挖掘不足": "需求确认不足",
    "需求挖掘与共情不足": "需求确认不足",
    "适配性不足": "适当性管理不足",
    "成交引导不足": "行动引导不足",
    "办理引导不足": "行动引导不足",
    "信息不足": "信息提供不足",
    "信息冗余": "信息过载",
    "表达重点不突出": "重点不突出",
    "重点不清晰": "重点不突出",
    "逻辑结构待加强": "逻辑结构不足",
    "客户共情不足": "共情不足",
    "共情挖掘不足": "共情不足",
    "异议处理能力不足": "异议处理不当",
    "客户关系处理不佳": "客户关系不佳",
    "强行推销": "强推销",
}

_CANONICAL_SET = set(CANONICAL_WEAKNESS_TAGS)


def _clean_tag(tag: object) -> str:
    value = re.sub(r"\s+", "", str(tag or ""))
    return value.strip("，,。；;：:、")


def normalize_weakness_tag(tag: object) -> str:
    """Return a stable employee-facing tag without fuzzy substring guessing."""
    value = _clean_tag(tag)
    if not value:
        return ""
    if value in _CANONICAL_SET:
        return value
    return _ALIASES.get(value, value)


def normalize_weakness_tags(tags: Iterable[object] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags or []:
        value = normalize_weakness_tag(tag)
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return normalized


def weakness_tag_matches(expected: object, detected: object) -> bool:
    """Match through canonical IDs; unknown labels require exact equality."""
    expected_value = normalize_weakness_tag(expected)
    detected_value = normalize_weakness_tag(detected)
    return bool(expected_value and expected_value == detected_value)
