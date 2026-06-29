from __future__ import annotations

import re


_SPACE_RE = re.compile(r"\s+")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = text.replace("\u3000", " ").replace("\r", "\n")
    normalized = _SPACE_RE.sub(" ", normalized)
    return normalized.strip()


def char_ngrams(text: str, n: int = 2) -> set[str]:
    value = clean_text(text)
    chars = [ch for ch in value if not ch.isspace()]
    if len(chars) < n:
        return set(chars)
    return {"".join(chars[i : i + n]) for i in range(len(chars) - n + 1)}


def lexical_similarity(a: str, b: str) -> float:
    grams_a = char_ngrams(a, 2) | char_ngrams(a, 1)
    grams_b = char_ngrams(b, 2) | char_ngrams(b, 1)
    if not grams_a or not grams_b:
        return 0.0
    return round(len(grams_a & grams_b) / len(grams_a | grams_b), 4)

