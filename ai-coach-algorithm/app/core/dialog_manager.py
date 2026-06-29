from __future__ import annotations

import os
import uuid
from typing import Any

from app.core.adaptive_difficulty import recommend_difficulty
from app.core.coverage import compute_intent_gap, update_covered_intents
from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.customer_profile_loader import get_customer_profile, load_customer_profiles
from app.core.llm_customer import generate_customer_question_with_llm
from app.core.llm_scorer import score_with_llm_finish
from app.core.marketing_rag import retrieve_marketing_knowledge
from app.core.memory_manager import get_memory_manager
from app.core.rule_scorer import score_employee_answer
from app.core.scoring_criteria_loader import get_primary_criterion
from app.core.weakness_profile import build_weakness_profile
from app.utils.file_loader import now_iso


DEFAULT_SCENE_ID = "INS_PERIODIC"
DEFAULT_TOTAL_ROUNDS = 3

# Scorer selection: "llm" tries DeepSeek first then falls back to rule;
# "rule" skips LLM entirely. Default to llm so the system uses the best
# scorer available, but a missing DEEPSEEK_API_KEY transparently degrades
# to rule_scorer — no behavior change for environments without a key.
_SCORER_PREFERENCE = os.getenv("AI_COACH_SCORER", "llm").lower()

# Customer-question generation: "llm" lets DeepSeek role-play the customer
# using the algorithm's gap / retrieval / profile signals as context; falls
# back to the CUSTOMER_INTENT_PROBES template on any failure or missing key.
# This is the original design — algorithm assists, LLM simulates.
_CUSTOMER_LLM_PREFERENCE = os.getenv("AI_COACH_CUSTOMER_LLM", "llm").lower()


async def _score_finish(
    answer: str,
    reference_items: list[dict[str, Any]],
    criterion: dict[str, Any],
    coverage: dict[str, Any],
    dialog_pairs: list[dict[str, Any]] | None = None,
    weakness_prompt: str = "",
) -> dict[str, Any]:
    """LLM-first, rule-fallback scoring at finish time (async)."""
    if _SCORER_PREFERENCE == "llm":
        llm_result = await score_with_llm_finish(
            answer,
            reference_items=reference_items,
            criterion=criterion,
            coverage=coverage,
            dialog_pairs=dialog_pairs,
            weakness_prompt=weakness_prompt,
        )
        if llm_result is not None:
            return llm_result
    # Rule scorer is sync (no I/O), call it directly — no need for to_thread
    return score_employee_answer(
        answer, reference_items, criterion=criterion, coverage=coverage
    )


def _build_dialog_pairs(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair each employee answer with the immediately preceding customer question.

    Walks the message history in order, holding the last customer message as
    context until the next employee message arrives, then emits a pair.
    Customer messages with no following employee reply (e.g. the final probe
    after the last round) are dropped.
    """
    pairs: list[dict[str, Any]] = []
    pending_customer: str | None = None
    for msg in messages:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "ai_customer":
            pending_customer = content
        elif role == "employee":
            pairs.append({
                "customer_question": pending_customer or "",
                "employee_answer": content,
            })
            pending_customer = None
    return pairs


# Sharp, in-character follow-up probes per customer concern, used to press the
# employee on a concern they have NOT yet addressed (the gap).
CUSTOMER_INTENT_PROBES = {
    "rate_concern": "那收益到底有多少？我感觉还是偏低，跟理财、存款比有什么优势？",
    "liquidity_concern": "那我万一中途要用钱、或者交不上了，能取出来吗？会不会亏？",
    "safety_concern": "那本金到底安不安全？万一亏了、或者公司出问题了怎么办？",
    "procedure_question": "那具体怎么办、要带什么材料、下一步我该做什么？",
    "rejection_or_hesitation": "我还是有点犹豫，你说的这些我得再想想，为什么我现在就得办？",
    "compliance_sensitive": "你刚才说的这个能不能给我保证？写进合同里吗，达不到怎么办？",
}


def list_profiles() -> list[dict[str, Any]]:
    return load_customer_profiles()


def start_dialogue(
    user_id: str = "U001",
    scene_id: str = DEFAULT_SCENE_ID,
    customer_id: str | None = None,
    task_id: str | None = None,
    total_rounds: int = DEFAULT_TOTAL_ROUNDS,
    difficulty: str | None = None,
    auto_difficulty: bool = True,
) -> dict[str, Any]:
    # Layer 3: 自适应难度 — 如果未指定 difficulty 且开启自动推荐，则根据历史成绩推荐
    difficulty_rec = None
    if not difficulty and not customer_id and auto_difficulty:
        difficulty_rec = recommend_difficulty(user_id=user_id, scene_id=scene_id)
        difficulty = difficulty_rec.recommended_difficulty

    profile = get_customer_profile(scene_id=scene_id, customer_id=customer_id, difficulty=difficulty)
    session_id = f"S_{uuid.uuid4().hex[:12]}"
    opening = profile.get("opening_question") or "您好，我想了解一下这个产品是否适合我。"

    # 查询用户历史弱点画像，注入 session 供后续 reply/finish 使用
    wp = build_weakness_profile(user_id=user_id, scene_id=scene_id)
    weakness_data: dict[str, Any] = {}
    if wp.has_history():
        weakness_data = {
            "profile": wp.to_dict(),
            "customer_prompt": wp.to_prompt_text(role="customer"),
            "scorer_prompt": wp.to_prompt_text(role="scorer"),
        }

    session = {
        "session_id": session_id,
        "user_id": user_id,
        "task_id": task_id,
        "scenario_id": profile.get("scene_id") or scene_id,
        "scene_id": profile.get("scene_id") or scene_id,
        "customer_id": profile.get("customer_id") or customer_id,
        "customer_type": profile.get("customer_type"),
        "difficulty_level": profile.get("difficulty_level") or difficulty or "中",
        "status": "running",
        "round": 1,
        "total_rounds": max(1, int(total_rounds)),
        "expected_intents": profile.get("expected_intents", []),
        "covered_intents": [],
        "weakness_profile": weakness_data,
        "messages": [{"role": "ai_customer", "content": opening, "created_at": now_iso()}],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    saved = get_memory_manager().upsert_session(session)
    result: dict[str, Any] = {"session": saved, "ai_customer_message": opening, "memory_status": get_memory_manager().status()}
    if difficulty_rec:
        result["difficulty_recommendation"] = difficulty_rec.to_dict()
    return result


async def reply_dialogue(session_id: str, employee_message: str) -> dict[str, Any]:
    """Async reply: generate the next customer follow-up only.

    Per-turn live scoring was removed — the final score is computed once at
    finish_dialogue over the whole conversation, so scoring every reply added
    LLM/token cost without changing the outcome the user sees. A reply now does
    just the intent/gap analysis needed to drive the next customer question.
    """
    manager = get_memory_manager()
    session = manager.get_session(session_id)
    if not session:
        raise KeyError(f"session not found: {session_id}")
    session.setdefault("messages", []).append({"role": "employee", "content": employee_message, "created_at": now_iso()})
    scene_id = session.get("scene_id") or session.get("scenario_id")
    total_rounds = int(session.get("total_rounds", DEFAULT_TOTAL_ROUNDS))
    # This reply closes the current round; if it was the last round, no new
    # question is generated and the front-end should call /dialog/finish next.
    current_round = int(session.get("round", 1))
    finished = current_round >= total_rounds

    intent = analyze_customer_answer(employee_message)
    # Accumulate which customer concerns the employee has addressed so far, then
    # compute the gap = expected concerns (from profile) minus what was covered.
    expected_intents = session.get("expected_intents", [])
    covered_intents = update_covered_intents(session.get("covered_intents", []), intent.get("intent_scores", {}))
    gap_intents = compute_intent_gap(expected_intents, covered_intents)

    retrieval: dict[str, Any] = {}
    next_question = None
    if not finished:
        # The gap drives both retrieval and the next follow-up question.
        # When finished there is no next question, so we skip retrieval entirely.
        retrieval = retrieve_marketing_knowledge(
            employee_message, route="customer", top_k=3, scene_id=scene_id, focus_intents=gap_intents or None
        )
        retrieval_items = retrieval.get("items", [])
        customer_weakness = (session.get("weakness_profile") or {}).get("customer_prompt", "")
        next_question = await _next_customer_question(
            session, employee_message, retrieval_items, intent, gap_intents, covered_intents,
            weakness_prompt=customer_weakness,
        )
        session["messages"].append({"role": "ai_customer", "content": next_question, "created_at": now_iso()})
        session["round"] = current_round + 1

    session["last_intent"] = intent
    session["covered_intents"] = covered_intents
    session["intent_gap"] = gap_intents
    saved = manager.upsert_session(session)
    return {
        "session": saved,
        "ai_customer_message": next_question,
        "round": session.get("round", current_round),
        "total_rounds": total_rounds,
        "finished": finished,
        "intent": intent,
        "expected_intents": expected_intents,
        "covered_intents": covered_intents,
        "intent_gap": gap_intents,
        "retrieval": retrieval,
    }


async def finish_dialogue(session_id: str) -> dict[str, Any]:
    manager = get_memory_manager()
    session = manager.get_session(session_id)
    if not session:
        raise KeyError(f"session not found: {session_id}")
    # Evaluate the WHOLE dialog, not just the last two messages — earlier good
    # responses should count, and a compliance violation anywhere in the session
    # should be visible to the scorer.
    employee_messages = [msg.get("content", "") for msg in session.get("messages", []) if msg.get("role") == "employee"]
    final_answer = "\n\n".join(msg for msg in employee_messages if msg)
    dialog_pairs = _build_dialog_pairs(session.get("messages", []))
    scene_id = session.get("scene_id")
    # Direct rubric lookup by scene; anchors tutor HyDE on the scenario's
    # must_points so omissions can be retrieved and penalized.
    criterion = get_primary_criterion(scene_id)
    retrieval = retrieve_marketing_knowledge(
        final_answer,
        route="tutor",
        top_k=3,
        scene_id=scene_id,
        must_points=criterion.get("must_points") or None,
        answer_goal=criterion.get("answer_goal"),
        key_terms=criterion.get("key_terms") or None,
    )
    coverage = retrieval.get("retrieval_trace", {}).get("must_point_coverage") or {}
    # Full rubric scoring: LLM-first (grounded in retrieved standard scripts +
    # criterion + coverage + full dialog trajectory), with rule_scorer as
    # fallback. The dialog_pairs let the LLM judge overall performance and
    # recognize recovery after a mistake. The method field on the result
    # records which path actually ran.
    wp_data = session.get("weakness_profile") or {}
    scorer_weakness = wp_data.get("scorer_prompt", "")
    score = await _score_finish(
        final_answer,
        retrieval.get("items", []),
        criterion=criterion,
        coverage=coverage,
        dialog_pairs=dialog_pairs,
        weakness_prompt=scorer_weakness,
    )
    score["criterion_id"] = criterion.get("criterion_id")
    score["must_point_coverage_rate"] = coverage.get("coverage_rate")
    session["status"] = "finished"
    session["score_result"] = score
    manager.upsert_session(session)
    record = {
        "memory_type": "long_term_dialogue",
        "session_id": session_id,
        "user_id": session.get("user_id"),
        "scenario_id": session.get("scenario_id") or session.get("scene_id"),
        "customer_id": session.get("customer_id"),
        "customer_type": session.get("customer_type"),
        "status": "finished",
        "summary": f"训练场景 {session.get('scenario_id') or session.get('scene_id')}，共 {len(employee_messages)} 轮员工回答，得分 {score['total_score']}。",
        "messages": session.get("messages", []),
        "score_result": score,
        "score": score["total_score"],
        "weakness_tags": score.get("weakness_tags", []),
        "feedback": _feedback(score),
        "created_at": session.get("created_at"),
    }
    saved_memory = manager.save_longterm(record)
    return {"session": session, "longterm_memory": saved_memory, "retrieval": retrieval}


async def _next_customer_question(
    session: dict[str, Any],
    employee_message: str,
    retrieval_items: list[dict[str, Any]],
    intent: dict[str, Any],
    gap_intents: list[str],
    covered_intents: list[str],
    weakness_prompt: str = "",
) -> str:
    """Pick the next customer follow-up (async).

    Original design: LLM simulates the customer, with the algorithm providing
    the gap + retrieval + profile as structured assistance. LLM is preferred
    because templates can't reason about conversation context — they repeat
    the same question whenever the keyword-based intent detector misses that
    a topic was actually covered. The template path remains as a safety net
    when no LLM is available.
    """
    if _CUSTOMER_LLM_PREFERENCE == "llm":
        profile = get_customer_profile(
            scene_id=session.get("scene_id") or session.get("scenario_id"),
            customer_id=session.get("customer_id"),
        ) or {}
        llm_text = await generate_customer_question_with_llm(
            profile=profile,
            messages=session.get("messages", []),
            employee_message=employee_message,
            gap_intents=gap_intents,
            covered_intents=covered_intents,
            retrieval_items=retrieval_items,
            weakness_prompt=weakness_prompt,
        )
        if llm_text:
            return llm_text

    # Template fallback (also used when AI_COACH_CUSTOMER_LLM=template).
    # 1. If the employee made a compliance-sensitive claim, the customer pounces.
    if "compliance_sensitive" in set(intent.get("intent_labels", [])):
        return CUSTOMER_INTENT_PROBES["compliance_sensitive"]
    # 2. Otherwise press the most important unaddressed concern (the gap).
    for label in gap_intents:
        if label in CUSTOMER_INTENT_PROBES:
            return CUSTOMER_INTENT_PROBES[label]
    # 3. No gap left -> all concerns addressed, move the conversation forward.
    if retrieval_items:
        return "你说的这些我大概明白了，那我现在适合办吗？需要怎么弄？"
    return "我明白了，那你建议我下一步怎么做？"


def _feedback(score: dict[str, Any]) -> str:
    weaknesses = score.get("weakness_tags") or []
    if weaknesses:
        return "建议下一轮重点补强：" + "、".join(weaknesses)
    return "整体表达较完整，下一轮可以继续加强需求确认和办理引导。"

