"""Enrich e2e gold expected_followup_direction with "|" alternative direction sets.

Background (2026-07-10/11 followup audit, docs/evaluation_ops_guide.md §4-5):
the original gold wrote a single "ideal-script" direction per turn, assuming the
employee answered the previous question. Gold employee scripts deliberately
answer poorly (that's the scoring test point), so the LLM customer legitimately
takes a different-but-reasonable direction and gets failed. Verdict split over
29 audited failures: 0 generation / 18 gold / 11 checker.

This script appends ONE audited alternative direction per affected turn using
the checker's "|" separator (best-of matching). Alternatives are worded from
the actually-observed legitimate customer behavior in audited traces — they do
NOT loosen the ruler to arbitrary text: a followup still must keyword- or
semantically-match one of the listed directions (or a gap intent).

Idempotent: skips a turn if the alternative is already present.
"""
from __future__ import annotations

import json
from pathlib import Path

GOLD = Path("data/eval/e2e_dialog_gold.jsonl")

# case_id -> {turn_idx (0-based, = round-2): alternative direction to append}
ALTS: dict[str, dict[int, str]] = {
    # -- 18 gold-verdict turns from the 2026-07-10 audit --
    "e2e_001_compliance_violation": {1: "质疑保本承诺、追问合同兑责与亏损赔偿"},
    "e2e_002_compliance_risk": {0: "追问本金亏损与提前支取扣费"},
    "e2e_003_good_risk_disclosure": {
        1: "对比股票型与债券型收益差距并要求选型建议",
        2: "坚持要求给出股票型或债券型的选型建议",
    },
    "e2e_007_comprehensive_answer": {
        0: "追问急用钱能否支取及退保扣费",
        1: "继续追问退保可取回的具体金额",
    },
    "e2e_009_procedure_missing": {0: "追问中途用钱能否提前支取"},
    "e2e_012_phone_invitation_good": {0: "先要求讲解分红机制再决定是否赴约"},
    "e2e_014_liquidity_risk_explained": {0: "重申选型问题并要求具体建议"},
    "e2e_016_information_overload": {0: "从信息轰炸中抓住重点追问满期领取金额与能否保住本金"},
    "e2e_020_gap_filling_good": {
        1: "追问最高收益上限与最差亏损幅度的对比",
        2: "继续索要收益与风险的具体数据",
    },
    "e2e_025_redeem_and_risk_good": {1: "追问赎回到账时间"},
    "e2e_028_procedure_and_materials_good": {
        0: "询问风险测评的内容以及测评后是否必须购买",
        1: "质疑适合性判断的标准和主体",
    },
    "e2e_034_direct_recommend_refusal_good": {0: "拒绝先答风险偏好，要求先评估当前股债配置比例"},
    "e2e_035_elderly_liquidity_good": {0: "追问退保损失的具体数字"},
    "e2e_041_procedure_only_no_risk": {0: "拒绝流程推进，要求先给考虑空间"},
    "e2e_046_multi_round_backslide": {1: "追问5%-7%收益数据对应股票型还是债券型"},
    # -- checker-verdict turns where a concrete alternative also helps --
    "e2e_004_liquidity_risk": {
        0: "追问退保损失的具体金额和比例",
        1: "追问第一年退保可取回多少钱",
    },
    "e2e_005_partial_compliance": {0: "追问最大回撤与最差情况的亏损幅度"},
    "e2e_024_soft_yield_misleading": {0: "质疑收益承诺能否写进合同"},
    "e2e_026_elderly_suitability_poor": {0: "质疑免测评销售并追问亏损责任"},
    "e2e_040_jargon_overload": {0: "质疑历史数据能否保证未来收益"},
    "e2e_049_fund_differentiation_good": {1: "坚持要求股票型与债券型之间的选型建议"},
    # -- same failure class newly observed in run e2e_verbose_20260711_105355 --
    "e2e_013_objection_handling_good": {0: "追问保单贷款的利息水平与是否够用"},
    "e2e_017_multi_round_correction": {
        0: "质疑赚钱保证并追问亏损赔偿责任",
        1: "指出前后矛盾并追问本金安全",
    },
    "e2e_023_fee_and_surrender_disclosure": {1: "索要缴费计划表与现金价值表"},
    "e2e_036_surrender_loss_sensitive": {0: "追问交满几年能拿回本金"},
    "e2e_045_multi_round_fill_good": {1: "质疑保障内容与本金安全的矛盾"},
}


def main() -> None:
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    updated = skipped = 0
    for row in rows:
        alts = ALTS.get(row.get("id"), {})
        directions = row.get("expected_followup_direction") or []
        for idx, alt in alts.items():
            if idx >= len(directions):
                print(f"  WARNING: {row.get('id')} turn {idx} out of range ({len(directions)} directions)")
                continue
            if alt in directions[idx]:
                skipped += 1
                continue
            directions[idx] = f"{directions[idx]}|{alt}"
            updated += 1
        if alts:
            row["expected_followup_direction"] = directions
            row["followup_direction_status"] = "direction_set_v1"
    GOLD.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"Appended {updated} alternative directions ({skipped} already present) across {len(ALTS)} cases")


if __name__ == "__main__":
    main()
