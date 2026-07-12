"""Widen e2e gold customer-retrieval evidence per the 2026-07-11 retrieval audit.

Same repair class as the followup direction sets: the per-turn evidence was
written for the ideal-script direction, but the retrieval query is driven by
the ACTUAL dialogue gap. Each edit below adds (or, for dead categories,
replaces with) the evidence category matching the audited actual customer
direction — evidence list semantics are OR, so this mirrors the "|" direction
sets. NOT touched: e2e_037 turn 0 (费用) — the audit confirmed a REAL retrieval
miss there (MCH_000154 费用结构 exists in WM_ASSET but is not recalled); that
failure signal must stay visible.

"清晰说明" (016/040) is removed outright: it is a tutor-side teaching category
with zero matchable wording in any customer corpus (dead combination, see
scripts/check_evidence_corpus_anchoring.py).

Idempotent: skips categories already present.
"""
from __future__ import annotations

import json
from pathlib import Path

GOLD = Path("data/eval/e2e_dialog_gold.jsonl")

# case_id -> {turn_idx: ("add"|"replace", [categories])}
EDITS: dict[str, dict[int, tuple[str, list[str]]]] = {
    "e2e_009_procedure_missing": {0: ("add", ["异议"])},          # 客户犹豫/追流动性，top-5为犹豫处理内容
    "e2e_016_information_overload": {0: ("replace", ["产品", "收益"])},  # 死类别"清晰说明"；客户抓重点问退保金额
    "e2e_020_gap_filling_good": {2: ("add", ["收益", "风险"])},    # 对齐followup方向集合"继续索要收益与风险数据"
    "e2e_029_internal_information_violation": {0: ("add", ["风险"])},  # FUND语料无合规文档(语料缺口)；客户质疑内幕风险
    "e2e_040_jargon_overload": {0: ("replace", ["风险"])},        # 死类别"清晰说明"；客户问回撤/本金
    "e2e_044_compliant_no_guidance": {0: ("add", ["收益"])},      # 客户实际追收益对比
    "e2e_045_multi_round_fill_good": {1: ("add", ["保障", "风险"])},  # 客户质疑保障内容与本金安全
    "e2e_046_multi_round_backslide": {
        1: ("add", ["收益"]),                                     # 客户继续追问收益差别
        2: ("add", ["收益"]),                                     # FUND语料无合规文档；客户质疑收益保证
    },
}


def main() -> None:
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    added = replaced = skipped = 0
    for row in rows:
        edits = EDITS.get(row.get("id"), {})
        evid = row.get("expected_customer_evidence_after_each_turn") or []
        for idx, (mode, cats) in edits.items():
            if idx >= len(evid):
                print(f"  WARNING: {row.get('id')} turn {idx} out of range ({len(evid)} turns)")
                continue
            if mode == "replace":
                if evid[idx] == cats:
                    skipped += 1
                    continue
                evid[idx] = list(cats)
                replaced += 1
            else:
                new = [c for c in cats if c not in evid[idx]]
                if not new:
                    skipped += 1
                    continue
                evid[idx] = evid[idx] + new
                added += 1
        if edits:
            row["expected_customer_evidence_after_each_turn"] = evid
            row["customer_evidence_status"] = "audited_v3"
    GOLD.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"Evidence sets: {added} widened, {replaced} dead-category replaced, {skipped} already applied "
          f"across {len(EDITS)} cases (e2e_037 left failing on purpose — real retrieval miss)")


if __name__ == "__main__":
    main()
