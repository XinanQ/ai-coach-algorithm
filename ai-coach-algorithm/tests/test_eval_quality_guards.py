from __future__ import annotations

import json
from pathlib import Path

from app.core.dialog_manager import _augment_llm_weakness_tags, _cross_check_coercive_sales
from app.core.weakness_taxonomy import normalize_weakness_tags, weakness_tag_matches
from app.core.marketing_rag import _intent_match_score
from eval.evidence import customer_evidence_from_direction
from eval.metrics import StageResult
from eval.report import build_report
from eval.stages._eval_e2e_impl import E2EEvaluator
from eval.transcript import transcript_hash
from eval.audit_provenance import (
    audit_context_fingerprint,
    scorer_gold_fingerprints,
    validate_tag_audit_source,
)


def test_weakness_taxonomy_normalizes_known_aliases_without_fuzzy_overlap() -> None:
    assert normalize_weakness_tags(["合规红线", "绝对化承诺", "成交引导不足"]) == [
        "合规问题",
        "不当承诺",
        "行动引导不足",
    ]
    assert weakness_tag_matches("风险说明缺失", "风险揭示不足")
    assert not weakness_tag_matches("信息过载", "重点不突出")
    assert not weakness_tag_matches("产品说明缺失", "收益说明缺失")


def test_transcript_hash_binds_reviewed_band_to_exact_dialogue() -> None:
    pairs = [{"customer_question": "收益有保证吗？", "employee_answer": "不承诺收益。"}]
    baseline = transcript_hash("FUND_GENERAL", pairs)
    assert baseline == transcript_hash("FUND_GENERAL", pairs)
    changed = [{**pairs[0], "employee_answer": "收益肯定有保证。"}]
    assert baseline != transcript_hash("FUND_GENERAL", changed)


def test_customer_route_evidence_uses_business_topics_not_behavior_boilerplate() -> None:
    assert customer_evidence_from_direction("客户可能确认赎回流程") == ["流动性", "办理"]
    assert customer_evidence_from_direction("客户可能反感邀约压力") == ["异议"]
    assert customer_evidence_from_direction("客户可能追问收益和风险") == ["收益", "风险"]
    assert customer_evidence_from_direction("客户可能决定") == []


def test_customer_intent_match_keeps_strong_single_gap_signal() -> None:
    text = "客户急用钱，想了解能否提前取。"
    single = _intent_match_score(["liquidity_concern"], text)
    multiple = _intent_match_score(["liquidity_concern", "rate_concern"], text)
    assert single > 0
    assert multiple == single


def test_explicit_per_turn_evidence_does_not_fall_back_for_unreviewed_turns() -> None:
    case = {
        "employee_messages": ["第一轮", "第二轮"],
        "expected_customer_evidence_after_each_turn": [["收益"]],
        "expected_customer_evidence": ["客户可能追问收益"],
    }
    assert E2EEvaluator._customer_evidence_for_turn(case, 0) == ["收益"]
    assert E2EEvaluator._customer_evidence_for_turn(case, 1) == []


def test_rule_tag_guard_augments_tags_without_changing_scores() -> None:
    score = {
        "total_score": 58,
        "dimension_scores": [{"key": "compliance", "score": 90, "weight": 0.3}],
        "weakness_tags": ["共情不足"],
        "method": "llm_scorer_deepseek_finish",
    }
    augmented = _augment_llm_weakness_tags(
        score,
        {"weakness_tags": ["信息过载", "重点不突出", "逻辑结构不足"]},
    )
    assert augmented["total_score"] == 58
    assert augmented["dimension_scores"][0]["score"] == 90
    assert augmented["weakness_tags"] == ["共情不足", "信息过载", "重点不突出"]
    assert augmented["method"].endswith("+rule_tag_guard")


def test_coercive_sales_cap_requires_family_override_signature_and_scarcity() -> None:
    score = {
        "total_score": 60,
        "dimension_scores": [
            {"key": "compliance", "score": 90, "weight": 0.30},
            {"key": "objection_handling", "score": 40, "weight": 0.30},
            {"key": "logic_structure", "score": 50, "weight": 0.20},
            {"key": "empathy", "score": 30, "weight": 0.20},
        ],
        "weakness_tags": [],
        "method": "llm_scorer_deepseek_finish",
    }
    capped = _cross_check_coercive_sales(
        score,
        "不用和家人商量了，这个名额有限，今天就签。",
    )
    assert capped["total_score"] <= 25
    assert {"异议处理不当", "客户关系不佳", "强推销"}.issubset(capped["weakness_tags"])
    assert capped["method"].endswith("+coercive_sales_cap")

    ordinary_pressure = {
        "total_score": 30,
        "dimension_scores": [],
        "weakness_tags": [],
        "method": "llm_scorer_deepseek_finish",
    }
    unchanged = _cross_check_coercive_sales(
        ordinary_pressure,
        "您明天必须来网点，这个名额就一个，别耽误。",
    )
    assert unchanged["total_score"] == 30
    assert unchanged["method"] == "llm_scorer_deepseek_finish"


def test_scorer_only_report_is_not_labeled_as_end_to_end() -> None:
    report = build_report([
        StageResult(
            stage="scorer_transcript",
            primary_metric="score_band_pass",
            value=0.94,
            gold_size=50,
            details={},
        )
    ], run_id="test_scorer_only")
    assert report["end_to_end_estimate"] is None
    assert report["end_to_end_metric_source"] == "unavailable"
    assert report["component_quality_estimate"] is None


def test_followup_semantic_fallback_is_explicit_and_thresholded(monkeypatch) -> None:
    evaluator = E2EEvaluator(skip_slow=True)
    try:
        monkeypatch.setattr(evaluator, "_semantic_similarity", lambda _a, _b: (0.72, "test"))
        monkeypatch.setattr(evaluator, "_semantic_threshold", lambda _backend: 0.60)
        result = evaluator._validate_followup(
            "那实际到手最差是不是只有3.5？",
            [],
            ["追问收益比较"],
            0,
        )
        assert result["pass"] is True
        assert result["method"] == "semantic_direction_match"

        monkeypatch.setattr(evaluator, "_semantic_similarity", lambda _a, _b: (0.20, "test"))
        result = evaluator._validate_followup(
            "那具体带什么材料？",
            [],
            ["追问收益比较"],
            0,
        )
        assert result["pass"] is False
        assert result["reason"] == "expected_direction_not_matched"
    finally:
        evaluator._tempdir.cleanup()


def test_eval_gold_has_route_specific_expectations_and_transcript_hashes() -> None:
    root = Path(__file__).resolve().parents[1]
    e2e_rows = [
        json.loads(line)
        for line in (root / "data/eval/e2e_dialog_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    scorer_rows = [
        json.loads(line)
        for line in (root / "data/eval/scorer_transcript_gold.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    tag_seed_rows = [
        json.loads(line)
        for line in (root / "data/eval/scorer_tag_review_seed.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(e2e_rows) == len(scorer_rows) == 50
    assert len(tag_seed_rows) == 50
    assert {row["id"] for row in tag_seed_rows} == {row["id"] for row in scorer_rows}
    assert all(row.get("evaluation_schema_version") == 2 for row in e2e_rows)
    assert all(row.get("dynamic_score_band_status") == "legacy_unbound" for row in e2e_rows)
    assert all(
        row.get("customer_evidence_status") in {"derived_v2", "reviewed", "audited_v3"}
        for row in e2e_rows
    )
    assert all("expected_customer_evidence" in row for row in e2e_rows)
    assert all("expected_customer_evidence_after_each_turn" in row for row in e2e_rows)
    assert all("expected_tutor_evidence" in row for row in e2e_rows)
    assert all(
        row.get("transcript_hash") == transcript_hash(row.get("scene_id"), row.get("dialog_pairs") or [])
        for row in scorer_rows
    )
    tag_statuses = {row.get("tag_status") for row in scorer_rows}
    assert len(tag_statuses) == 1
    assert tag_statuses.issubset({"pending", "human_reviewed_exhaustive_v1"})


def test_score_and_tag_gold_fingerprints_are_independent() -> None:
    base = [{
        "id": "case_1",
        "scene_id": "FUND_GENERAL",
        "dialog_pairs": [{"customer_question": "风险呢？", "employee_answer": "有风险。"}],
        "expected_score_range": [50, 70],
        "strict_score_range": [55, 65],
        "quality": "partial",
        "band_status": "reviewed",
        "transcript_hash": "hash",
        "expected_weak_tags": ["行动引导不足"],
        "tag_status": "pending",
    }]
    changed_tags = [{**base[0], "expected_weak_tags": ["共情不足"]}]
    changed_score = [{**base[0], "expected_score_range": [40, 60]}]
    base_fp = scorer_gold_fingerprints(base)
    assert scorer_gold_fingerprints(changed_tags)["score_gold_fingerprint"] == base_fp["score_gold_fingerprint"]
    assert scorer_gold_fingerprints(changed_tags)["tag_gold_fingerprint"] != base_fp["tag_gold_fingerprint"]
    assert scorer_gold_fingerprints(changed_score)["score_gold_fingerprint"] != base_fp["score_gold_fingerprint"]


def test_tag_audit_source_rejects_subset_or_stale_report() -> None:
    gold = [{"id": "case_1", "expected_weak_tags": [], "tag_status": "pending"}]
    fps = scorer_gold_fingerprints(gold)
    report = {
        "stage": "scorer_transcript",
        "details": {
            "selected_case_ids": [],
            "total_cases": 1,
            "transcript_integrity_pass": 1.0,
            "scorer_method_distribution": {"llm_scorer_deepseek_finish": 1},
            "tag_gold_fingerprint": fps["tag_gold_fingerprint"],
            "tag_case_results": [{"id": "case_1", "expected_tags": [], "detected_tags": []}],
        },
    }
    assert validate_tag_audit_source(report, gold) == []
    report["details"]["selected_case_ids"] = ["case_1"]
    assert "subset scorer reports cannot seed a tag audit" in validate_tag_audit_source(report, gold)
    report["details"]["selected_case_ids"] = []
    report["details"]["tag_gold_fingerprint"] = "stale"
    assert "report tag gold fingerprint is missing or stale" in validate_tag_audit_source(report, gold)


def test_tag_audit_context_binds_detected_tags_and_transcript() -> None:
    base = dict(
        case_id="case_1",
        tag="共情不足",
        kind="fp",
        expected_tags=[],
        detected_tags=["共情不足"],
        seed_tags=[],
        pending_tags=[],
        transcript_hash="hash-a",
        tag_gold_fingerprint="gold-a",
        tag_seed_fingerprint="seed-a",
    )
    assert audit_context_fingerprint(**base) != audit_context_fingerprint(
        **{**base, "detected_tags": ["共情不足", "行动引导不足"]}
    )
