"""Evaluate LLM-based intent detection: 4 strategies compared.

Strategies:
  1. keyword-only   — existing keyword+semantic fusion pipeline
  2. llm-only       — pure LLM classification
  3. llm-primary    — LLM first, keyword fallback when LLM returns empty
  4. union          — keyword ∪ LLM

Usage:
    python -m eval.stages.eval_llm_intent --sample 50
    python -m eval.stages.eval_llm_intent --sample 0   # all 193 rows
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.core.embedding_adapter import get_embedding_adapter
from app.core.intent_labels import INTENT_LABELS
from app.core.llm.client import is_llm_available
from app.core.llm_customer import _parse_customer_response
from app.core.llm_scorer import _call_llm_text
from app.core.marketing_rag import (
    INTENT_ABS_FLOOR,
    INTENT_MAX_LABELS,
    INTENT_REL_RATIO,
    _build_customer_query_plan,
    _select_intent_labels,
)
from eval.metrics import StageResult, multilabel_prf1

GOLD_PATH = Path("data/intent_eval_gold.jsonl")
DEFAULT_RESULT_PATH = Path("data/eval/llm_intent_eval.json")

INTENT_LIST_STR = ", ".join(INTENT_LABELS)

LLM_INTENT_PROMPT = f"""你是一个金融营销场景的意图分类器。
给定一段员工或客户的话,判断这段话涉及了以下哪些客户顾虑/意图(可多选,也可为空):
{INTENT_LIST_STR}

规则:
- 只标注这段话**实际涉及**的顾虑,不推测
- 如果这段话不涉及任何顾虑(比如是操作说明、背景描述等),返回空数组
- 返回严格 JSON,不许多余文字

输出格式:
{{"intents": ["label1", "label2"], "follow_up": "占位"}}
"""


def load_gold(path: Path = GOLD_PATH) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


async def _call_llm_intent(text: str) -> list[str]:
    messages = [
        {"role": "system", "content": LLM_INTENT_PROMPT},
        {"role": "user", "content": text},
    ]
    raw = await _call_llm_text(messages, method="eval_intent", temperature=0.1)
    if not raw:
        return []
    parsed = _parse_customer_response(raw)
    if parsed:
        return parsed.get("intents", [])
    return []


async def evaluate(
    *,
    sample_size: int = 50,
    verbose: bool = False,
) -> dict[str, Any]:
    rows = load_gold()

    if not is_llm_available():
        raise RuntimeError("DeepSeek API key not configured. Set DEEPSEEK_API_KEY in .env")

    if 0 < sample_size < len(rows):
        import random
        random.seed(42)
        rows = random.sample(rows, sample_size)

    adapter = get_embedding_adapter()

    gold_sets: list[set[str]] = []
    kw_sets: list[set[str]] = []
    llm_sets: list[set[str]] = []
    primary_sets: list[set[str]] = []
    union_sets: list[set[str]] = []
    details: list[dict[str, Any]] = []

    for i, row in enumerate(rows):
        text = row["text"]
        gold = set(row.get("gold_labels") or [])
        gold_sets.append(gold)

        plan = _build_customer_query_plan(text, adapter)
        kw_labels = set(_select_intent_labels(plan["fused_intent_scores"]))
        kw_sets.append(kw_labels)

        llm_labels = set(await _call_llm_intent(text))
        llm_sets.append(llm_labels)

        # llm-primary: use LLM, fall back to keyword only when LLM returns empty
        primary = llm_labels if llm_labels else kw_labels
        primary_sets.append(primary)

        union = kw_labels | llm_labels
        union_sets.append(union)

        if verbose:
            details.append({
                "id": row.get("id", f"#{i}"),
                "text": text[:50],
                "gold": sorted(gold),
                "kw": sorted(kw_labels),
                "llm": sorted(llm_labels),
                "primary": sorted(primary),
            })

        progress = f"[{i+1}/{len(rows)}]"
        best = "llm" if llm_labels == gold else ("kw" if kw_labels == gold else "---")
        g, k, l = str(sorted(gold)), str(sorted(kw_labels)), str(sorted(llm_labels))
        print(f"  {progress} gold={g:<45} kw={k:<45} llm={l:<35} winner={best}", flush=True)

    strategies = {
        "keyword_only": multilabel_prf1(gold_sets, kw_sets, labels=INTENT_LABELS),
        "llm_only": multilabel_prf1(gold_sets, llm_sets, labels=INTENT_LABELS),
        "llm_primary": multilabel_prf1(gold_sets, primary_sets, labels=INTENT_LABELS),
        "union": multilabel_prf1(gold_sets, union_sets, labels=INTENT_LABELS),
    }

    result: dict[str, Any] = {"sample_size": len(rows)}
    for name, m in strategies.items():
        result[name] = {
            "micro_precision": round(m["micro_precision"], 4),
            "micro_recall": round(m["micro_recall"], 4),
            "micro_f1": round(m["micro_f1"], 4),
        }

    print(f"\n{'=' * 60}")
    print(f"  LLM Intent Evaluation — {len(rows)} samples")
    print(f"{'=' * 60}")
    print(f"  {'Strategy':<16} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print(f"  {'-' * 48}")
    for name in ["keyword_only", "llm_only", "llm_primary", "union"]:
        m = result[name]
        marker = " <-- best" if m["micro_f1"] == max(result[n]["micro_f1"] for n in ["keyword_only", "llm_only", "llm_primary", "union"]) else ""
        print(f"  {name:<16} {m['micro_precision']:>10.4f} {m['micro_recall']:>10.4f} {m['micro_f1']:>10.4f}{marker}")
    print(f"{'=' * 60}")

    if verbose and details:
        print("\n--- Per-sample Details ---")
        for d in details:
            print(json.dumps(d, ensure_ascii=False))

    return result


def load_cached_result(path: Path = DEFAULT_RESULT_PATH) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        result = json.load(f)
    result.setdefault("result_source", f"cached:{path.as_posix()}")
    return result


def _to_stage_result(result: dict[str, Any]) -> StageResult:
    primary = result.get("llm_only") or {}
    details = {
        "result_source": result.get("result_source", "live_deepseek_eval"),
        "strategies": {
            name: result[name]
            for name in ["keyword_only", "llm_only", "llm_primary", "union"]
            if name in result
        },
    }
    return StageResult(
        stage="llm_intent_detection",
        primary_metric="llm_only_micro_f1",
        value=float(primary.get("micro_f1", 0.0)),
        gold_size=int(result.get("sample_size", 0)),
        details=details,
    )


def evaluate_stage(
    *,
    sample_size: int = 50,
    verbose: bool = False,
    cached_ok: bool = True,
) -> StageResult:
    """Run LLM intent evaluation for the unified report.

    If DeepSeek is not configured, fall back to the last saved
    data/eval/llm_intent_eval.json result so local `run_all` still reflects the
    upgraded LLM-intent benchmark instead of silently reverting to the legacy
    keyword-only bottleneck.
    """
    if is_llm_available():
        result = asyncio.run(evaluate(sample_size=sample_size, verbose=verbose))
        result["result_source"] = "live_deepseek_eval"
        return _to_stage_result(result)
    if cached_ok and DEFAULT_RESULT_PATH.exists():
        return _to_stage_result(load_cached_result())
    raise RuntimeError("DeepSeek API key not configured and no cached LLM intent eval result found")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=50, help="0 = all rows")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        result = asyncio.run(evaluate(sample_size=args.sample, verbose=args.verbose))
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc

    out_path = DEFAULT_RESULT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
