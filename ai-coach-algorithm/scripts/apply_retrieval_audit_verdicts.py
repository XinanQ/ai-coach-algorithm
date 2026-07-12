"""Apply AI-assisted verdicts to retrieval_audit.jsonl (2026-07-11 batch, trace e2e_verbose_20260711_124900).

Verdict taxonomy:
  retrieval — top-5 与证据要求无关且语料中存在应命中文档（检索算法问题）
  gold      — 证据类别锚定理想脚本方向 / 死类别 / 场景语料缺口（gold 问题）
  checker   — 正确文档已在 top-5，同义词表未锚定语料措辞（校验器问题）

Reviewer: AI-assisted (Claude), pending human spot-check. Structural findings:
1) 合规 synonym list uses formal regulatory tokens the corpus never writes; the
   corpus phrases compliance as 不实承诺/夸大/诱导/保监会 (e2e_001 rank-1 hit missed).
2) Evidence-per-turn was written for the ideal script direction — same root
   cause as the followup audit: the retrieval query is driven by the ACTUAL
   dialogue gap, so ideal-script evidence is unreachable when the customer
   presses a different (legitimate) direction.
3) "清晰说明" is a tutor-side teaching category; customer-route corpora contain
   no such meta-language — a dead combination that can never pass.
4) e2e_037 is the single REAL retrieval miss: MCH_000154 (费用结构:管理费/手续费)
   exists in WM_ASSET and answers the customer's exact fee question but was not
   recalled into top-5. Kept failing; belongs to the retrieval-improvement backlog.
"""
from __future__ import annotations

import json
from pathlib import Path

AUDIT = Path("data/eval/retrieval_audit.jsonl")

# (case_id, round) -> (verdict, note)
V: dict[tuple[str, int], tuple[str, str]] = {
    ("e2e_001_compliance_violation", 2): ("checker", "合规注意事项文档(MCH_000075:不实承诺/保监会/诱导)已在rank-1，同义词表却要求'监管/规定/红线'等语料不用的词"),
    ("e2e_009_procedure_missing", 2): ("gold", "客户实际方向是犹豫/流动性(gap=rejection)，'办理'证据来自理想脚本；top-5确为异议处理内容"),
    ("e2e_016_information_overload", 2): ("gold", "'清晰说明'为死类别：通俗/简明是教学侧措辞，客户语料不存在；客户实际抓重点问退保金额"),
    ("e2e_020_gap_filling_good", 4): ("gold", "客户实际继续索要收益/风险数据(与followup方向集合一致)，'异议'证据来自理想脚本的'表示考虑'"),
    ("e2e_029_internal_information_violation", 2): ("gold", "FUND_GENERAL语料无合规类文档，'合规'证据无从命中——语料建设缺口；客户实际质疑内幕消息风险"),
    ("e2e_037_fee_sensitive_good", 2): ("retrieval", "真实检索缺陷：MCH_000154(费用结构:管理费0.13-0.2%/手续费0.15%)在语料中且直接回答客户费用问题，未被召回top-5。保留失败，入检索backlog"),
    ("e2e_040_jargon_overload", 2): ("gold", "'清晰说明'死类别，同016；客户实际追问回撤/本金风险"),
    ("e2e_044_compliant_no_guidance", 2): ("gold", "客户实际追问收益对比(gap=rate)，'办理'证据来自理想脚本"),
    ("e2e_045_multi_round_fill_good", 3): ("gold", "客户实际质疑保障内容与本金安全，'合同'证据来自理想脚本的'确认条款'"),
    ("e2e_046_multi_round_backslide", 3): ("gold", "客户实际继续追问收益差别，'办理'证据来自理想脚本的'确认购买'"),
    ("e2e_046_multi_round_backslide", 4): ("gold", "FUND_GENERAL语料无合规文档(同029)；客户实际质疑收益保证能否写进合同"),
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
