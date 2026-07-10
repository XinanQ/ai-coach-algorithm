"""Apply AI-assisted verdicts to followup_audit.jsonl (2026-07-10 batch, trace e2e_verbose_20260710_230251).

Verdict taxonomy:
  generation — 追问真的偏题/重复/画像不符（生成器问题）
  gold       — 追问合理，但 expected_direction 只写了理想脚本的单一方向（gold 问题）
  checker    — 方向语义命中但校验器没接住：阈值边缘/期望文本抽象/无gold兜底弱（校验器问题）

Reviewer: AI-assisted (Claude), pending human spot-check. Key structural finding:
expected_direction assumes the employee ANSWERED the previous question, but gold
employee scripts deliberately don't (that's the scoring test point) — the LLM
customer correctly re-presses the unanswered question and gets failed for it.
"""
from __future__ import annotations

import json
from pathlib import Path

AUDIT = Path("data/eval/followup_audit.jsonl")

# (case_id, round) -> (verdict, note)
V: dict[tuple[str, int], tuple[str, str]] = {
    ("e2e_001_compliance_violation", 3): ("gold", "员工刚说'绝对保本'，客户追问敢不敢写进合同完全合理；gold只写了'追问收益率'单一方向"),
    ("e2e_002_compliance_risk", 2): ("gold", "客户问'会不会亏本金'是风险理解的自然延伸；gold单一期望'追问收益'"),
    ("e2e_003_good_risk_disclosure", 3): ("gold", "员工刚报4-6%收益，客户嫌低是rate_concern自然延续；gold期望跳到本金安全"),
    ("e2e_003_good_risk_disclosure", 4): ("gold", "员工没答收益对比，客户继续追对比合理；gold期望'确认购买流程'是理想脚本线"),
    ("e2e_004_liquidity_risk", 3): ("checker", "'扣多少'就是费用明细，sim 0.5514仅差阈值0.58一点，典型阈值边缘假阴性"),
    ("e2e_005_partial_compliance", 2): ("checker", "'最大回撤多少'就是本金安全的具体化，embedding没捕捉领域等价"),
    ("e2e_007_comprehensive_answer", 2): ("gold", "客户问亏本追责合理；gold期望'确认保障内容'是理想线"),
    ("e2e_007_comprehensive_answer", 3): ("gold", "员工持续回避，客户死磕本金问题正确；gold期望'追问收益示例'"),
    ("e2e_009_procedure_missing", 2): ("gold", "客户问提前取钱（流动性）合理；gold单一期望'追问如何办理'"),
    ("e2e_012_phone_invitation_good", 2): ("checker", "客户行为就是'提出异议'（拒绝赴约要先解释），命中expected后半句但语义匹配没接住"),
    ("e2e_014_liquidity_risk_explained", 2): ("gold", "员工跑题，客户重申选型问题合理；gold期望'确认赎回流程'"),
    ("e2e_014_liquidity_risk_explained", 3): ("checker", "无gold无gap时兜底太弱：客户合理重申核心问题被判no_relevance"),
    ("e2e_016_information_overload", 2): ("gold", "客户从信息轰炸中抓重点问退保损失，恰是对信息过载的真实反应；expected'迷失信息重点'写法不可匹配"),
    ("e2e_020_gap_filling_good", 3): ("gold", "客户要债基收益对比数据，rate_concern深挖合理；gold期望'追问风险'"),
    ("e2e_020_gap_filling_good", 4): ("gold", "员工没给数据，客户继续要对比合理；gold期望'表示考虑'"),
    ("e2e_024_soft_yield_misleading", 2): ("checker", "'写进合同还是随便说的'就是'追问收益是否保证'，明显假阴性"),
    ("e2e_025_redeem_and_risk_good", 3): ("gold", "员工上轮讲赎回规则，客户问到账时间是自然延续；gold期望'追问净值波动'"),
    ("e2e_026_elderly_suitability_poor", 2): ("checker", "'亏了谁负责+敢保证只赚不赔'就是本金安全+适当性质疑，明显命中expected"),
    ("e2e_027_phone_invitation_pressure", 2): ("checker", "客户开口'别催我'就是反感邀约压力，明显命中expected"),
    ("e2e_028_procedure_and_materials_good", 2): ("gold", "员工只讲流程无视犹豫，客户表达'看完不合适呢'合理；gold期望'确认渠道材料'"),
    ("e2e_028_procedure_and_materials_good", 3): ("gold", "客户问责'漏条款谁负责'与期望'追问条款内容'接近但方向不同，gold单一方向"),
    ("e2e_033_contract_boundary_good", 2): ("checker", "'条款里写清楚了吗'就是'追问条款具体内容'，明显假阴性"),
    ("e2e_034_direct_recommend_refusal_good", 2): ("gold", "刁钻客户拒绝先答风险偏好、坚持要建议，真实行为；gold假设客户配合回答"),
    ("e2e_035_elderly_liquidity_good", 2): ("gold", "客户追问退保数字合理；gold期望'确认其他产品选择'"),
    ("e2e_040_jargon_overload", 2): ("checker", "'专业名词我听不太懂'就是'迷失专业术语'，明显命中expected"),
    ("e2e_041_procedure_only_no_risk", 2): ("gold", "员工催单，客户问'为什么要现在办'合理；gold期望'追问风险收益'"),
    ("e2e_041_procedure_only_no_risk", 3): ("checker", "无gold兜底弱：客户对催单的合理反感被判no_relevance"),
    ("e2e_046_multi_round_backslide", 3): ("gold", "客户澄清5-7%是股型还是债型，合理；gold期望'确认购买'"),
    ("e2e_049_fund_differentiation_good", 3): ("checker", "无gold兜底弱：客户要选型建议被判no_relevance"),
}


def main() -> None:
    rows = [json.loads(line) for line in AUDIT.read_text(encoding="utf-8").splitlines() if line.strip()]
    updated = missing = 0
    for row in rows:
        key = (row.get("case_id"), row.get("round"))
        if key in V and not row.get("verdict"):
            row["verdict"], row["note"] = V[key]
            updated += 1
        elif key not in V:
            missing += 1
            print(f"  no verdict prepared for {key}")
    AUDIT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    from collections import Counter
    counts = Counter(r["verdict"] for r in rows if r.get("verdict"))
    print(f"Updated {updated} rows ({missing} unmatched). Verdict split: {dict(counts)} / {len(rows)} total")


if __name__ == "__main__":
    main()
