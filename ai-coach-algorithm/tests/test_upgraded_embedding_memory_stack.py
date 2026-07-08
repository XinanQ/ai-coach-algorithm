from __future__ import annotations

import re
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.embedding_adapter import EmbeddingAdapter
from app.core.embedding_builder import build_marketing_vector_index
from app.core.memory_manager import MemoryManager
from app.core.memory_store import HybridLongTermMemoryStore, HybridShortTermMemoryStore
from app.core.marketing_rag import retrieve_marketing_knowledge
from app.main import app


def test_hash_embedding_adapter_is_deterministic() -> None:
    adapter = EmbeddingAdapter(backend="hash", dimensions=64)
    first = adapter.embed_query("客户担心提前取出影响收益")
    second = adapter.embed_query("客户担心提前取出影响收益")
    assert len(first) == 64
    assert first == second
    assert adapter.describe()["active_backend"] == "local_hash"


def test_chroma_vector_index_build_and_retrieve_with_hash_backend(tmp_path: Path, monkeypatch) -> None:
    import app.core.chroma_vector_store as chroma_vector_store

    monkeypatch.setattr(chroma_vector_store, "CHROMA_DIR", tmp_path / "chroma")
    monkeypatch.setattr(chroma_vector_store, "MANIFEST_PATH", tmp_path / "manifest.json")
    monkeypatch.setattr(chroma_vector_store, "JSON_MIRROR_PATH", tmp_path / "marketing_vector_index.json")
    result = build_marketing_vector_index(force=True, embedding_backend="hash", dimensions=64)
    assert result["vector_backend"] == "chroma"
    assert result["chunk_count"] > 0
    tutor_retrieved = retrieve_marketing_knowledge("客户担心定期提前支取是否方便", route="tutor", top_k=3)
    assert tutor_retrieved["items"]
    assert tutor_retrieved["retrieval_backend"] in {"chroma", "json_lexical_fallback"}
    assert tutor_retrieved["retrieval_algorithm"] == "tutor_hyde_chroma_fusion_v1"
    assert "hypothetical_answer" in tutor_retrieved["retrieval_trace"]["hyde"]

    customer_retrieved = retrieve_marketing_knowledge("客户说别的银行利率更高，我应该怎么追问", route="customer", top_k=3)
    assert customer_retrieved["items"]
    assert customer_retrieved["retrieval_algorithm"] == "customer_intent_embedding_keyword_fusion_v1"
    assert customer_retrieved["retrieval_trace"]["query_plan"]["intent_labels"]


def test_memory_manager_json_fallback_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AI_COACH_SHORT_MEMORY_BACKEND", "json")
    monkeypatch.setenv("AI_COACH_LONG_MEMORY_BACKEND", "json")
    manager = MemoryManager(
        short_store=HybridShortTermMemoryStore(json_path=str(tmp_path / "sessions.json")),
        long_store=HybridLongTermMemoryStore(json_path=str(tmp_path / "longterm.json")),
    )
    session = manager.upsert_session({"session_id": "S_TEST", "user_id": "U001", "messages": []})
    assert session["session_id"] == "S_TEST"
    manager.append_message("S_TEST", "employee", "我先了解您的资金安排，再推荐期限。")
    assert manager.get_session("S_TEST")["messages"]
    saved = manager.save_longterm(
        {
            "session_id": "S_TEST",
            "user_id": "U001",
            "scenario_id": "DEP_001",
            "summary": "员工能够先询问资金安排。",
            "weakness_tags": [],
        }
    )
    assert saved["memory_id"].startswith("MEM_")
    assert manager.retrieve_history("资金安排", user_id="U001")


def test_practice_task_catalog_returns_display_ready_cards() -> None:
    client = TestClient(app)
    tasks = client.get("/practice/tasks")
    assert tasks.status_code == 200
    body = tasks.json()
    assert body["levelName"] == "Lv5 专业进阶"
    assert body["selectedTab"] == "self"
    assert body["selectedDirection"] is None
    assert body["total"] == 39
    assert body["returned"] == 39
    assert [item["label"] for item in body["directions"]] == [
        "客户触达",
        "需求识别",
        "产品讲解",
        "异议处理",
        "成交促成",
        "合规风险",
        "售后维护",
    ]
    direction_counts = {item["key"]: 0 for item in body["directions"]}
    for item in body["list"]:
        direction_counts[item["direction"]] += 1
        assert 6 <= item["totalRounds"] <= 10
        assert item["minRounds"] <= item["targetRounds"] <= item["maxRounds"]
        assert item["totalRounds"] == item["maxRounds"]
        assert item["roundPolicy"]["source"] == "dynamic_policy"
    assert all(count > 0 for count in direction_counts.values())
    for direction in body["directions"]:
        filtered = client.get("/practice/tasks", params={"direction": direction["key"]})
        assert filtered.status_code == 200
        filtered_body = filtered.json()
        assert filtered_body["total"] == direction_counts[direction["key"]]
        assert {item["direction"] for item in filtered_body["list"]} == {direction["key"]}
    assert body["list"]
    card = body["list"][0]
    assert {"taskId", "sceneId", "customerId", "title", "category", "durationText", "tags"} <= set(card)
    assert card["tags"] and all("_" not in tag for tag in card["tags"])
    assert card["intentTags"] and any("_" in tag for tag in card["intentTags"])

    detail = client.get(f"/practice/tasks/{card['taskId']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["openingQuestion"]
    assert detail_body["scriptEntry"]["label"] == "查看标准话术"
    assert detail_body["scriptEntry"]["count"] > 0
    assert detail_body["scriptCards"]

    scripts = client.get(f"/practice/tasks/{card['taskId']}/scripts")
    assert scripts.status_code == 200
    scripts_body = scripts.json()
    assert scripts_body["taskId"] == card["taskId"]
    assert scripts_body["total"] > 0
    script_card = scripts_body["list"][0]
    assert {
        "scriptId",
        "title",
        "displayTitle",
        "sourceTitle",
        "subtitle",
        "tags",
        "standardSpeech",
        "copyText",
        "sourceFile",
        "sourceScope",
    } <= set(script_card)
    assert script_card["title"] == script_card["displayTitle"]
    assert not re.match(r"^[（(]?[一二三四五六七八九十百千万\d]+[、.)）]", script_card["displayTitle"])
    assert script_card["sourceScope"] in {"exact_scene", "same_business"}
    assert script_card["standardSpeech"]
    assert script_card["tags"]

    dividend_scripts = client.get("/practice/tasks/TASK_CUST_RATE_DIVIDEND_LOW/scripts")
    assert dividend_scripts.status_code == 200
    dividend_cards = dividend_scripts.json()["list"]
    assert any(card["displayTitle"] == "客户质疑前期收益低时怎么解释" for card in dividend_cards)
    assert {card["sourceScope"] for card in dividend_cards} == {"exact_scene"}

    script_detail = client.get(
        f"/practice/scripts/{script_card['scriptId']}",
        params={"taskId": card["taskId"]},
    )
    assert script_detail.status_code == 200
    assert script_detail.json()["standardSpeech"] == script_card["standardSpeech"]

    profiles = client.get("/dialog/profiles")
    assert profiles.status_code == 200
    profile = profiles.json()["profiles"][0]
    assert profile["tags"] and all("_" not in tag for tag in profile["tags"])


def test_reviewed_script_title_override_takes_precedence(tmp_path: Path, monkeypatch) -> None:
    from app.core import script_title_review
    from app.core.script_materials import get_script_card

    override_path = tmp_path / "script_title_overrides.json"
    override_path.write_text(
        json.dumps(
            {
                "overrides": {
                    "MCH_000068": {
                        "displayTitle": "审核后的分红险前期收益解释",
                        "status": "approved",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(script_title_review, "SCRIPT_TITLE_OVERRIDES_PATH", override_path)
    script_title_review.clear_script_title_override_cache()
    try:
        card = get_script_card("MCH_000068", task_id="TASK_CUST_RATE_DIVIDEND_LOW")
        assert card is not None
        assert card["displayTitle"] == "审核后的分红险前期收益解释"
        assert card["title"] == "审核后的分红险前期收益解释"
    finally:
        script_title_review.clear_script_title_override_cache()
    assert profile["expectedIntents"] and any("_" in tag for tag in profile["expectedIntents"])


def test_api_health_and_dialog_flow() -> None:
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    task_list = client.get("/practice/tasks").json()["list"]
    auto_task = next(item for item in task_list if item["direction"] in {"objection", "close", "compliance"})
    auto_start = client.post("/dialog/start", json={"user_id": "U_AUTO", "task_id": auto_task["taskId"]})
    assert auto_start.status_code == 200
    auto_body = auto_start.json()
    assert auto_body["taskId"] == auto_task["taskId"]
    assert auto_body["totalRounds"] == auto_body["maxRounds"]
    assert 6 <= auto_body["totalRounds"] <= 10
    assert auto_body["minRounds"] <= auto_body["targetRounds"] <= auto_body["maxRounds"]
    assert auto_body["roundPolicy"]["effective_source"] == "dynamic_policy"

    start = client.post("/dialog/start", json={"user_id": "U_TEST", "scene_id": "INS_PERIODIC"})
    assert start.status_code == 200
    start_body = start.json()
    session_id = start_body["sessionId"]
    assert 6 <= start_body["totalRounds"] <= 10 and start_body["round"] == 1
    assert start_body["totalRounds"] == start_body["maxRounds"]
    assert start_body["roundPolicy"]["effective_source"] == "dynamic_policy"
    assert start_body["messages"] and start_body["messages"][0]["role"] == "ai"
    # Early reply: not yet finished, AI follow-up returned.
    # Per-turn live scoring is intentionally removed; score/source are only
    # returned once by /dialog/finish.
    reply1 = client.post(
        "/dialog/reply",
        json={"session_id": session_id, "employee_message": "我先了解您的资金安排，这款期交保险需要每年持续缴费，请以保险合同为准。"},
    )
    assert reply1.status_code == 200
    reply1_body = reply1.json()
    assert reply1_body["finished"] is False
    assert reply1_body["message"] is not None
    assert "liveScore" not in reply1_body
    assert "source" not in reply1_body
    assert reply1_body["totalRounds"] == start_body["totalRounds"]
    finish = client.post("/dialog/finish", json={"session_id": session_id})
    assert finish.status_code == 200
    finish_body = finish.json()
    # presenter adapts to the 联调 contract: camelCase + 4-dimension scores
    assert "score" in finish_body and finish_body["score"] >= 0
    assert finish_body["source"] == "RULE_BASED"
    dimension_names = {d["name"] for d in finish_body["dimensionScores"]}
    assert {"合规度", "异议处理", "逻辑结构", "共情力"} <= dimension_names
