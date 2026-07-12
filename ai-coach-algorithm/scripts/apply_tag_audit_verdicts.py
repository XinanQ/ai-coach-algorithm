"""Prepare verdict proposals in tag_audit.jsonl for explicit review.

Verdict taxonomy (see build_tag_audit.py):
  fp: justified     — transcript really shows the weakness; gold is non-exhaustive -> add to gold
      spurious      — detector over-report; keep failing (detector backlog)
  fn: detector_miss — real weakness not reported; keep failing (detector backlog)
      gold_wrong    — expected tag doesn't hold on re-read -> remove from gold

This script creates proposals only. It never writes an accepted `verdict`:
every row must be explicitly checked against the frozen transcript and marked
`review_status=human_reviewed` with a reviewer before gold can be changed.

Consistent judging rules used for the borderline tags (spot-check against
transcript excerpts in tag_audit.jsonl):

共情不足 — spurious when (a) the employee DID use an empathy phrase
  ("我理解您…" in 021/031/032/033/036/037/038), or (b) the customer voiced no
  worry/emotion, just neutral questions (012/020/023/027/029/044/046/047/048).
  justified only when the customer expressed worry/hesitation/frustration and
  the employee never acknowledged it.
逻辑结构不足 — justified only when the reply itself is disorganized
  (016/040 info-dump). "答非所问" belongs to 异议处理不当, not logic ->
  spurious on 003/005/006/009/035/037.
标准要点覆盖不足 — spurious on 016/040 where the info-dump actually covers the
  standard points (the defect is overload, not missing points); justified
  elsewhere (short scripts genuinely miss points).
行动引导不足 — all 5 fp spurious: each dialog HAS explicit next-step guidance
  (012/047 邀约, 018/039 提供/整理资料, 022 催签 — over-guidance, not lack).
红线类 (合规问题/不当承诺/风险揭示不足/收益说明不规范/强推销/客户关系不佳) —
  judged strictly against actual wording: justified only when a concrete
  violating utterance exists (e.g. 017 "肯定赚钱", 042 "收益很稳定",
  050 "先买着问题不大", 026 "不用测评直接买"); spurious when the transcript
  contains proper disclosure (017/046 风险揭示不足 — 轮内确有"不保本不保息")
  or no such conduct (048 合规问题, 001 强推销, 026 客户关系不佳, 020 收益说明).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

AUDIT = Path("data/eval/tag_audit.jsonl")

# (case_id, tag) -> reason. Rows are fp unless noted; kind checked at apply time.
SPURIOUS: dict[tuple[str, str], str] = {
    # ---- 共情不足: employee did empathize (R1) ----
    ("scorer_e2e_021_family_decision_respected", "共情不足"): "员工首轮'您想和家人商量是很合理的'即共情认可",
    ("scorer_e2e_031_guarantee_refusal_good", "共情不足"): "员工首轮'我理解您对资金安全的担忧'",
    ("scorer_e2e_032_max_yield_range_good", "共情不足"): "员工首轮'我理解您关心收益'",
    ("scorer_e2e_033_contract_boundary_good", "共情不足"): "员工首轮'我理解您希望把承诺写进合同'",
    ("scorer_e2e_036_surrender_loss_sensitive", "共情不足"): "员工首轮'我理解您关心退保损失'",
    ("scorer_e2e_037_fee_sensitive_good", "共情不足"): "员工首轮'我理解您关心费用'",
    ("scorer_e2e_038_redeem_time_sensitive", "共情不足"): "员工有'我理解您关心到账时间'共情句式；真实缺陷是跑题(已由异议处理/客户关系覆盖)",
    # ---- 共情不足: customer voiced no emotion, neutral inquiry (R2) ----
    ("scorer_e2e_012_phone_invitation_good", "共情不足"): "电话场景客户中性问分红，无情绪诉求；缺陷是未答问题(异议处理)",
    ("scorer_e2e_020_gap_filling_good", "共情不足"): "客户中性追问收益数字，无担忧情绪，各轮应答规范",
    ("scorer_e2e_023_fee_and_surrender_disclosure", "共情不足"): "客户中性追问具体数字，员工揭示到位，无情绪需回应",
    ("scorer_e2e_027_phone_invitation_pressure", "共情不足"): "电话场景客户中性问分红",
    ("scorer_e2e_029_internal_information_violation", "共情不足"): "客户中性问选型，无情绪诉求；缺陷是违规话术",
    ("scorer_e2e_044_compliant_no_guidance", "共情不足"): "客户中性追问收益对比，无情绪诉求",
    ("scorer_e2e_046_multi_round_backslide", "共情不足"): "客户中性追问收益数字，无情绪诉求",
    ("scorer_e2e_047_phone_respect_time_good", "共情不足"): "电话场景客户中性问分红，员工礼貌尊重时间",
    ("scorer_e2e_048_phone_pressure_poor", "共情不足"): "客户中性问分红；缺陷是强推销非共情",
    # ---- 逻辑结构不足: reply not disorganized, defect is 答非所问 ----
    ("scorer_e2e_003_good_risk_disclosure", "逻辑结构不足"): "各轮回答内部结构清楚，第3轮是答非所问(异议处理)非逻辑混乱",
    ("scorer_e2e_005_partial_compliance", "逻辑结构不足"): "回答简短结构完整，缺陷是回避核心诉求",
    ("scorer_e2e_006_information_insufficient", "逻辑结构不足"): "仅一句话，无所谓逻辑结构，缺陷是零信息",
    ("scorer_e2e_009_procedure_missing", "逻辑结构不足"): "回答简短结构完整，缺陷是未回应中途用钱",
    ("scorer_e2e_035_elderly_liquidity_good", "逻辑结构不足"): "回答结构完整(共情+揭示+替代推荐)，缺陷是未量化",
    ("scorer_e2e_037_fee_sensitive_good", "逻辑结构不足"): "两轮回答各自结构完整，缺陷是不给具体费率",
    # ---- 标准要点覆盖不足: info-dump cases actually cover the points ----
    ("scorer_e2e_016_information_overload", "标准要点覆盖不足"): "信息轰炸恰恰覆盖了全部标准要点(缴费/保障/分红/退保/犹豫期…)，缺陷是过载非缺要点",
    ("scorer_e2e_040_jargon_overload", "标准要点覆盖不足"): "术语轰炸中风险等级/回撤/收益等要点均在，缺陷是不通俗非缺要点",
    # ---- 行动引导不足: dialogs HAVE explicit guidance ----
    ("scorer_e2e_012_phone_invitation_good", "行动引导不足"): "员工明确邀约来网点=有行动引导",
    ("scorer_e2e_018_customer_empathy_good", "行动引导不足"): "员工'提供更详细的产品资料供参考'=有下一步引导",
    ("scorer_e2e_022_family_decision_pressure", "行动引导不足"): "'今天就签'是过度引导而非引导不足",
    ("scorer_e2e_039_family_respect_good", "行动引导不足"): "'整理资料给您，确认后随时联系我'=明确行动方案",
    ("scorer_e2e_047_phone_respect_time_good", "行动引导不足"): "员工在约具体时间=有行动引导",
    # ---- 红线类: no concrete violating/proper conduct mismatch ----
    ("scorer_e2e_017_multi_round_correction", "风险揭示不足"): "轮2明确'不保本不保息收益不确定'=有风险揭示",
    ("scorer_e2e_046_multi_round_backslide", "风险揭示不足"): "前两轮有'投资有风险不承诺保本'揭示，缺陷在轮3倒退(已由合规/不当承诺覆盖)",
    ("scorer_e2e_048_phone_pressure_poor", "合规问题"): "施压邀约无收益承诺/违规陈述，属强推销(已检出)非合规红线",
    ("scorer_e2e_001_compliance_violation", "强推销"): "违规是虚假承诺与答非所问，无'必须买/不买就没'式施压话术",
    ("scorer_e2e_026_elderly_suitability_poor", "客户关系不佳"): "无威胁/贬低/不尊重话术，缺陷是违规推销(已由强推销/适当性覆盖)",
    ("scorer_e2e_020_gap_filling_good", "收益说明不规范"): "'历史8%-12%+历史不代表未来'是规范表述",
    # ---- 信息提供不足 ----
    ("scorer_e2e_034_direct_recommend_refusal_good", "信息提供不足"): "员工在合理挖掘需求(good样本)，反问是正确动作而非拒供信息",
}

# (case_id, tag) -> reason, for fn rows.
GOLD_WRONG: dict[tuple[str, str], str] = {
    ("scorer_e2e_009_procedure_missing", "办理流程缺失"): "客户处于犹豫期未问办理，此对话的核心弱点是未回应中途用钱与无引导(行动引导不足已标)，'办理流程缺失'不成立",
}


def main() -> None:
    rows = [json.loads(line) for line in AUDIT.read_text(encoding="utf-8").splitlines() if line.strip()]
    proposed = kept = 0
    for row in rows:
        if row.get("review_status") == "human_reviewed" and row.get("verdict"):
            kept += 1
            continue
        # Legacy runs wrote defaults directly into verdict. Clear those so
        # they cannot masquerade as independent human labels.
        row["verdict"] = ""
        row["note"] = ""
        row["review_status"] = "pending"
        row["reviewer"] = ""
        row["reviewed_at"] = ""
        key = (row["case_id"], row["tag"])
        if row["kind"] == "fp":
            if key in SPURIOUS:
                row["proposed_verdict"], row["proposal_note"] = "spurious", SPURIOUS[key]
            else:
                row["proposed_verdict"] = "justified"
                row["proposal_note"] = "候选：对话可能展现该弱点，需逐条确认"
        else:
            if key in GOLD_WRONG:
                row["proposed_verdict"], row["proposal_note"] = "gold_wrong", GOLD_WRONG[key]
            else:
                row["proposed_verdict"] = "detector_miss"
                row["proposal_note"] = "候选：可能是真实漏检，需逐条确认"
        proposed += 1
    AUDIT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    counts = Counter((r["kind"], r.get("proposed_verdict")) for r in rows)
    print(
        f"Prepared {proposed} proposals ({kept} completed reviews kept). "
        f"Proposal split: {dict(counts)} / {len(rows)} total; no verdict was auto-approved."
    )


if __name__ == "__main__":
    main()
