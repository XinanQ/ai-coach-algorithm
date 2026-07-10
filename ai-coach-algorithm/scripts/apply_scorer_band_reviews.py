"""Apply band reviews to scorer_transcript_gold.jsonl (2026-07-10 batch).

Review method: each frozen transcript judged independently against the anchor
table BEFORE comparing with the LLM's actual score (防止凑数):
  85+   合规 + 每个客户问题被正面回答 + 有引导
  70-85 合规 + 大部分接住,个别回避
  55-70 合规、信息真实,但答非所问明显或共情/引导缺失
  40-55 无违规但全程回避核心问题
  <30   命中合规红线 / 绕过适当性,一票封顶
Only rows still in band_status="draft" are touched; the 5 previously
reviewed rows are left as-is. Reviewer: AI-assisted (Claude), pending 20%
human spot-check per eval policy.
"""
from __future__ import annotations

import json
from pathlib import Path

GOLD = Path("data/eval/scorer_transcript_gold.jsonl")

# id -> (band, quality, note)
REVIEWS: dict[str, tuple[list[int], str, str]] = {
    "scorer_e2e_001_compliance_violation": ([0, 25], "poor", "保本保息+绝对保本多重红线，第3轮再答非所问，一票封顶。"),
    "scorer_e2e_002_compliance_risk": ([45, 60], "partial", "两轮合规声明规范，但客户情绪质问'能保证什么'仅回'看合同'，无共情无解释；合规好异议处理弱。"),
    "scorer_e2e_004_liquidity_risk": ([50, 65], "partial", "轮1有退保损失揭示；轮2客户要具体数字被推向说明书，部分回应部分回避。"),
    "scorer_e2e_006_information_insufficient": ([20, 40], "poor", "'这是一款很好的保险产品'零信息且答非所问，无违规但近乎空洞推销。原带宽合理。"),
    "scorer_e2e_008_bad_risk_disclosure": ([0, 25], "poor", "'基本没风险/公司大肯定没问题/收益很稳定每年都能分红'多重红线封顶；原[0,55]过宽收紧。"),
    "scorer_e2e_009_procedure_missing": ([45, 60], "partial", "产品信息真实（缴费期/保障/收益看经营），但未回应'中途用钱'核心问题。"),
    "scorer_e2e_012_phone_invitation_good": ([40, 55], "partial", "电话邀约礼貌，但客户问分红多少完全未答直接邀约；原good是模板口径。"),
    "scorer_e2e_013_objection_handling_good": ([60, 75], "partial", "轮1优秀（共情+保单贷款正面回应流动性）；轮2利息细节被'更灵活交费'带过。原[80,95]偏高。"),
    "scorer_e2e_014_liquidity_risk_explained": ([50, 65], "partial", "轮1风险揭示规范；轮2客户要选型建议却答赎回规划，跑题。"),
    "scorer_e2e_015_compliance_sensitive_avoided": ([45, 60], "partial", "客户问取钱扣多少，答'监管要求不能承诺收益'——拿合规挡流动性问题，答非所问。"),
    "scorer_e2e_016_information_overload": ([40, 55], "partial", "设计为信息轰炸case：信息真实含风险提示，但无视客户'要商量'且重点全无。"),
    "scorer_e2e_017_multi_round_correction": ([25, 45], "partial", "轮1'肯定赚钱'违规，轮2明确纠错值得认可，轮3又回避取钱；违规事实+纠错行为对冲。"),
    "scorer_e2e_018_customer_empathy_good": ([55, 70], "partial", "共情和不催单是真实亮点，但'能不能取、扣多少'两轮都没答。原[80,95]是模板口径。"),
    "scorer_e2e_019_objection_handling_poor": ([20, 40], "poor", "'不买就没了'威胁式推销，零风险揭示；无收益红线故不到封顶档。原带宽合理。"),
    "scorer_e2e_020_gap_filling_good": ([60, 75], "partial", "风险定位、历史收益+免责均规范，轮3转推低风险产品算部分回应适配性。"),
    "scorer_e2e_021_family_decision_respected": ([60, 75], "partial", "尊重商量+主动整理费用/退保损失/风险提示资料，有行动方案；未给具体数字。"),
    "scorer_e2e_022_family_decision_pressure": ([0, 25], "poor", "'不用和家人商量今天就签'强推+无视客户意愿+零风险揭示，恶劣度等同红线；原[20,40]偏松。"),
    "scorer_e2e_023_fee_and_surrender_disclosure": ([55, 70], "partial", "退保低于已交保费+现价表+现金流确认建议，揭示到位；缺具体数字。"),
    "scorer_e2e_024_soft_yield_misleading": ([0, 25], "poor", "'基本都能拿到/收益不会差/放心买'软性收益承诺红线，封顶。"),
    "scorer_e2e_025_redeem_and_risk_good": ([55, 70], "partial", "不承诺收益+净值波动+赎回规则+测评引导均规范；未答最大亏损数字。"),
    "scorer_e2e_026_elderly_suitability_poor": ([0, 25], "poor", "'不用测评直接买'绕过适当性+'收益肯定比活期高'承诺，双重违规封顶。"),
    "scorer_e2e_027_phone_invitation_pressure": ([20, 40], "poor", "'必须来/名额有限'施压邀约，无红线但强推销。原带宽合理。"),
    "scorer_e2e_028_procedure_and_materials_good": ([50, 65], "partial", "合规流程讲解规范，但客户两次表达'要考虑/别逼我'均被无视，只顾推进流程。"),
    "scorer_e2e_029_internal_information_violation": ([0, 25], "poor", "'内部消息/大概率涨/收益肯定比公开高'严重违规封顶。原带宽正确。"),
    "scorer_e2e_030_platform_safety_false": ([0, 25], "poor", "'大银行平台本金不用担心不会亏'虚假安全承诺红线封顶；原[20,45]偏松。"),
    "scorer_e2e_031_guarantee_refusal_good": ([55, 70], "partial", "拒绝承诺本身合规，但客户只是要股/债收益差的大概参考（合理请求），两轮拿监管挡回属过度拒绝。原[85,95]是模板口径。"),
    "scorer_e2e_032_max_yield_range_good": ([55, 70], "partial", "共情+历史3-5%区间+以合同为准，规范；最大回撤未正面回答。"),
    "scorer_e2e_033_contract_boundary_good": ([50, 65], "partial", "合同边界解释规范，但'能不能取、扣多少'被推向说明书。"),
    "scorer_e2e_034_direct_recommend_refusal_good": ([65, 80], "good", "解释不直接推荐的原因+主动挖掘风险承受与期限，客户配合回答，真实的好对话。"),
    "scorer_e2e_035_elderly_liquidity_good": ([55, 70], "partial", "共情+退保损失揭示+推荐短期理财替代（适配意识好）；'损失多少'未量化。"),
    "scorer_e2e_036_surrender_loss_sensitive": ([60, 75], "partial", "低于已交保费+现价表+现金流确认，揭示与引导均在；缺具体数字。原[85,95]偏高。"),
    "scorer_e2e_037_fee_sensitive_good": ([50, 65], "partial", "两轮都未给具体费率，仅'说明书里有/中长期占比低'；费用敏感客户核心诉求未满足。"),
    "scorer_e2e_038_redeem_time_sensitive": ([35, 50], "partial", "客户两次问股/债选型，员工两次答到账时间，跑题到客户质疑'装傻'；无违规但沟通失败。原[85,95]严重失配。"),
    "scorer_e2e_039_family_respect_good": ([60, 75], "partial", "尊重商量+整理资料方案；取钱问题未量化回答。"),
    "scorer_e2e_040_jargon_overload": ([40, 55], "partial", "夏普比率/摊余成本术语轰炸，有回撤数字但不通俗，未回应配置调整问题。"),
    "scorer_e2e_041_procedure_only_no_risk": ([35, 50], "partial", "只讲办理流程，无视'考虑考虑'还催'今天办吗'，轻度强推+零风险揭示。"),
    "scorer_e2e_042_yield_only_no_risk": ([0, 25], "poor", "'收益很稳定'承诺+两轮回避本金问题，红线封顶；原[15,30]微调对齐封顶原则。"),
    "scorer_e2e_043_empathy_only_no_product": ([40, 55], "partial", "纯共情零产品信息，两轮均未回答取钱问题。"),
    "scorer_e2e_044_compliant_no_guidance": ([45, 60], "partial", "合规免责语两轮复读，无任何实质信息或引导。"),
    "scorer_e2e_045_multi_round_fill_good": ([45, 60], "partial", "信息渐进补全（保障→不保本→读条款）但客户的取钱问题三轮始终未答。原[65,82]偏高。"),
    "scorer_e2e_046_multi_round_backslide": ([0, 25], "poor", "前两轮合规，第3轮'内部分析收益肯定比公开高'倒退违规，封顶。原[15,30]对齐封顶。"),
    "scorer_e2e_047_phone_respect_time_good": ([30, 50], "partial", "邀约礼貌且尊重客户时间，但分红问题完全未答；电话场景下礼貌与跑题对冲。"),
    "scorer_e2e_048_phone_pressure_poor": ([15, 35], "poor", "'必须来/名额一个/别耽误'强推销。原带宽合理。"),
    "scorer_e2e_049_fund_differentiation_good": ([50, 65], "partial", "净值化解释规范，但'哪个亏本概率大'被泛化回避。原带宽合理。"),
    "scorer_e2e_050_low_risk_mismatch_poor": ([0, 25], "poor", "低风险测评客户被推R4且'先买着问题不大'，适当性严重违规封顶；原[20,45]偏松。"),
}


def main() -> None:
    rows = [json.loads(line) for line in GOLD.read_text(encoding="utf-8").splitlines() if line.strip()]
    updated = skipped = 0
    for row in rows:
        review = REVIEWS.get(row.get("id"))
        if review is None or row.get("band_status") != "draft":
            skipped += 1
            continue
        band, quality, note = review
        row["expected_score_range"] = band
        row["quality"] = quality
        row["band_status"] = "reviewed"
        row["note"] = note
        updated += 1
    GOLD.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"Updated {updated} rows, left {skipped} untouched (already reviewed or not in review map).")


if __name__ == "__main__":
    main()
