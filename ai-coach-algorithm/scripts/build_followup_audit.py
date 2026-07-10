"""Build the follow-up checker credibility audit sheet from an e2e verbose trace.

Why: followup_pass dropped 0.92 → 0.50 after the checker was tightened.
Before optimizing the customer-question generator against that number, we must
know how much of the 0.50 is real generation failure vs. measurement error —
otherwise we risk tuning a sharp, realistic customer into a template-parrot
that merely matches the gold's expected directions. (Same failure class as the
old keyword checker's false negatives, sign flipped.)

The sheet lists every FAILED follow-up turn with the data needed for a
three-way human verdict:
    generation — 追问真的偏题/重复/画像不符（生成问题）
    gold       — 追问合理，但 gold 只写了一个可接受方向（gold 问题）
    checker    — 方向语义命中，校验器没接住（校验器问题）

It also reports the gold-coverage split (turns with no expected_direction)
so the 0.50 的口径 is explicit.

Usage:
    python scripts/build_followup_audit.py                 # newest trace
    python scripts/build_followup_audit.py --trace <path>
Output:
    data/eval/followup_audit.jsonl  (existing verdicts are preserved)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

OUT_PATH = Path("data/eval/followup_audit.jsonl")


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
    if not transcripts or "turns" not in (transcripts[0] or {}):
        raise SystemExit(
            f"{trace_path.name} has no per-turn follow-up data. "
            "Regenerate the trace with the updated eval (per-turn `turns` field)."
        )

    existing = {(r.get("case_id"), r.get("round")): r for r in _load_jsonl(args.out)}

    total = covered = auto_pass_no_gold = failed = 0
    rows: list[dict] = []
    for case in transcripts:
        for turn in case.get("turns", []):
            if turn.get("ai_customer_message") is None:
                continue
            total += 1
            has_gold = bool(turn.get("expected_direction"))
            covered += has_gold
            if not has_gold:
                auto_pass_no_gold += turn.get("followup_pass") is not False
            if turn.get("followup_pass") is False:
                failed += 1
                key = (case.get("case_id"), turn.get("round"))
                prior = existing.get(key, {})
                rows.append({
                    "case_id": case.get("case_id"),
                    "scene_id": case.get("scene_id"),
                    "round": turn.get("round"),
                    "customer_question": turn.get("ai_customer_message"),
                    "expected_direction": turn.get("expected_direction"),
                    "gap_intents": turn.get("gap_intents"),
                    "checker_reason": turn.get("followup_reason"),
                    "checker_method": turn.get("followup_method"),
                    # human verdict fields — fill these in
                    "verdict": prior.get("verdict", ""),  # generation | gold | checker
                    "note": prior.get("note", ""),
                    "source_trace": trace_path.name,
                })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    verdicts = [r["verdict"] for r in rows if r["verdict"]]
    print(f"trace: {trace_path.name}")
    print(f"turns total={total}  gold-covered={covered} ({covered / total:.2%})  "
          f"no-gold-auto-pass={auto_pass_no_gold}")
    print(f"failed follow-up turns written for audit: {len(rows)} -> {args.out}")
    if verdicts:
        from collections import Counter
        print(f"verdicts so far: {dict(Counter(verdicts))} ({len(verdicts)}/{len(rows)} judged)")
    else:
        print("Next: fill `verdict` (generation|gold|checker) per row, then rerun to see the split.")


if __name__ == "__main__":
    main()
