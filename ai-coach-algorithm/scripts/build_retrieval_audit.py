"""Build the customer-retrieval evidence audit sheet from an e2e verbose trace.

Why: customer_retrieval_hit is stuck at 0.78-0.80 (10 case failures) and now
caps dynamic_dialogue_pass. Before touching the retrieval algorithm we must
know how much of that is real retrieval failure vs. measurement error — the
known sample (e2e_001 round 2) shows the checker demanding synonym tokens
("监管/规定/红线") that the scene corpus never uses, while the retrieval had
already placed the correct compliance document at rank 1.

The sheet lists every FAILED customer-retrieval turn for a three-way verdict:
    retrieval — top-5 内容确实与证据要求无关（检索算法问题）
    gold      — 证据词与场景语料措辞脱节，正确文档无法字面命中（gold 问题）
    checker   — 正确文档已在 top-5，但同义词表没接住（校验器问题）

Usage:
    python scripts/build_retrieval_audit.py                 # newest trace
    python scripts/build_retrieval_audit.py --trace <path>
Output:
    data/eval/retrieval_audit.jsonl  (existing verdicts are preserved)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

OUT_PATH = Path("data/eval/retrieval_audit.jsonl")


def _latest_trace() -> Path | None:
    candidates = sorted(Path("data/eval").glob("e2e_verbose_*.json"), reverse=True)
    return candidates[0] if candidates else None


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    trace_path = args.trace or _latest_trace()
    if trace_path is None or not trace_path.exists():
        raise SystemExit(
            "No e2e_verbose_*.json found. Run: "
            "python -m eval.stages.eval_e2e --verbose --save-trace"
        )
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    details = trace.get("result", {}).get("details", {}) or trace.get("details", {})
    transcripts = details.get("case_transcripts") or []
    if not transcripts or "retrieval_hit" not in ((transcripts[0] or {}).get("turns") or [{}])[0]:
        raise SystemExit(
            f"{trace_path.name} has no per-turn retrieval data. "
            "Regenerate the trace with the updated eval "
            "(python -m eval.stages.eval_e2e --verbose --save-trace)."
        )

    existing = {(r.get("case_id"), r.get("round")): r for r in _load_jsonl(args.out)}

    total = failed = 0
    failed_cases: set[str] = set()
    rows: list[dict] = []
    for case in transcripts:
        for turn in case.get("turns", []):
            total += 1
            if turn.get("retrieval_hit") is False:
                failed += 1
                failed_cases.add(case.get("case_id"))
                key = (case.get("case_id"), turn.get("round"))
                prior = existing.get(key, {})
                rows.append({
                    "case_id": case.get("case_id"),
                    "scene_id": case.get("scene_id"),
                    "round": turn.get("round"),
                    "expected_evidence": turn.get("expected_retrieval_evidence"),
                    "checker_reason": turn.get("retrieval_reason"),
                    "missing_core_keywords": turn.get("missing_core_keywords"),
                    "retrieval_top_titles": turn.get("retrieval_top_titles"),
                    "retrieval_top_snippets": turn.get("retrieval_top_snippets"),
                    # human verdict fields — fill these in
                    "verdict": prior.get("verdict", ""),  # retrieval | gold | checker
                    "note": prior.get("note", ""),
                    "source_trace": trace_path.name,
                })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    verdicts = [r["verdict"] for r in rows if r["verdict"]]
    print(f"trace: {trace_path.name}")
    print(f"turns total={total}  failed retrieval turns={failed} "
          f"across {len(failed_cases)} cases: {sorted(failed_cases)}")
    print(f"written for audit: {len(rows)} -> {args.out}")
    if verdicts:
        from collections import Counter
        print(f"verdicts so far: {dict(Counter(verdicts))} ({len(verdicts)}/{len(rows)} judged)")
    else:
        print("Next: fill `verdict` (retrieval|gold|checker) per row, then rerun to see the split.")


if __name__ == "__main__":
    main()
