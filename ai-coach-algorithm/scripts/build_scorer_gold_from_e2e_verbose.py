"""Build scorer_transcript_gold.jsonl candidates from an e2e verbose trace.

Takes the REAL dialogs produced by an LLM-customer e2e run (customer
questions from the trace, employee answers from e2e_dialog_gold.jsonl) and
freezes them into fixed transcripts for the scorer_transcript eval stage.

Every generated case is marked band_status="draft" with the score band copied
from the old e2e gold — those bands were calibrated on the rule scorer, so a
human MUST re-review each band against the frozen transcript ("这段对话该得
多少分") and flip band_status to "reviewed" before the number is citable.

Usage:
    python scripts/build_scorer_gold_from_e2e_verbose.py
    python scripts/build_scorer_gold_from_e2e_verbose.py --verbose-path data/eval/e2e_verbose_20260709_192657.json

Existing gold entries are preserved: cases whose id already exists in the
output file are skipped, so manual reviews are never overwritten.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

E2E_GOLD_PATH = Path("data/eval/e2e_dialog_gold.jsonl")
OUT_PATH = Path("data/eval/scorer_transcript_gold.jsonl")


def _latest_verbose() -> Path | None:
    candidates = sorted(Path("data/eval").glob("e2e_verbose_*.json"), reverse=True)
    return candidates[0] if candidates else None


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _build_pairs(sample: dict, employee_messages: list[str]) -> list[dict]:
    """Zip customer questions (opening + per-round follow-ups) with answers.

    Supports both trace shapes:
      - case_transcripts entries: {"opening": ..., "customer_messages": [...]}
      - legacy failure_samples entries: {"start_trace": {"opening"}, "reply_results": [...]}
    """
    if "customer_messages" in sample:
        questions = [sample.get("opening", ""), *sample.get("customer_messages", [])]
    else:
        questions = [sample.get("start_trace", {}).get("opening", "")]
        for reply in sample.get("reply_results", []):
            msg = reply.get("ai_customer_message")
            if msg:
                questions.append(msg)
    pairs = []
    for i, answer in enumerate(employee_messages):
        question = questions[i] if i < len(questions) else ""
        pairs.append({"customer_question": question, "employee_answer": answer})
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose-path", type=Path, default=None)
    parser.add_argument("--gold-path", type=Path, default=E2E_GOLD_PATH)
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    verbose_path = args.verbose_path or _latest_verbose()
    if verbose_path is None or not verbose_path.exists():
        raise SystemExit("No e2e_verbose_*.json found. Run: python -m eval.stages.eval_e2e --verbose --save-trace")

    with open(verbose_path, encoding="utf-8") as f:
        trace = json.load(f)
    details = trace.get("result", {}).get("details", {}) or trace.get("details", {})
    # Prefer the full per-case transcripts (all 50 cases); fall back to the
    # failure-only samples for traces produced by older eval versions.
    samples = details.get("case_transcripts") or details.get("failure_samples") or []
    e2e_gold = {case["id"]: case for case in _load_jsonl(args.gold_path)}

    existing_ids: set[str] = set()
    existing_rows: list[dict] = []
    if args.out.exists():
        existing_rows = _load_jsonl(args.out)
        existing_ids = {row.get("id") for row in existing_rows}

    new_rows = []
    for sample in samples:
        case_id = sample.get("case_id")
        gold_case = e2e_gold.get(case_id)
        out_id = f"scorer_{case_id}"
        if gold_case is None or out_id in existing_ids:
            continue
        employee_messages = gold_case.get("employee_messages") or []
        pairs = _build_pairs(sample, employee_messages)
        if not pairs:
            continue
        new_rows.append({
            "id": out_id,
            "scene_id": gold_case.get("scene_id"),
            "dialog_pairs": pairs,
            # Copied from rule-scorer-era gold — MUST be human-reviewed.
            "expected_score_range": gold_case.get("expected_score_range", [0, 100]),
            "expected_weak_tags": gold_case.get("expected_weak_tags", []),
            "quality": gold_case.get("quality", ""),
            "band_status": "draft",
            "note": f"auto-built from {verbose_path.name}; band copied from e2e gold, review before use",
        })

    if not new_rows:
        print("No new candidates (all case ids already present, or trace has no failure samples).")
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for row in [*existing_rows, *new_rows]:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(new_rows)} new draft cases (total {len(existing_rows) + len(new_rows)}) to {args.out}")
    print("Next: human-review each expected_score_range, then set band_status=\"reviewed\".")


if __name__ == "__main__":
    main()
