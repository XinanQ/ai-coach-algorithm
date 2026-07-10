from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from app.core.adaptive_difficulty import recommend_difficulty
from app.core.coverage import compute_intent_gap, update_covered_intents
from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.customer_profile_loader import get_customer_profile, load_customer_profiles
from app.core.dialog_round_policy import (
    DEFAULT_TARGET_ROUNDS,
    MAX_DIALOG_ROUNDS,
    MIN_DIALOG_ROUNDS,
    build_dialog_round_policy,
)
from app.core.llm_customer import (
    generate_customer_question_stream,
    generate_customer_question_with_llm,
    warm_customer_prefix,
)
from app.core.llm_scorer import score_with_llm_finish
from app.core.marketing_rag import retrieve_marketing_knowledge
from app.core.memory_manager import get_memory_manager
from app.core.practice_catalog import get_practice_task_detail
from app.core.rule_scorer import detect_compliance_violation, score_employee_answer
from app.core.scoring_criteria_loader import get_primary_criterion
from app.core.weakness_profile import build_weakness_profile
from app.utils.file_loader import now_iso


logger = logging.getLogger(__name__)

DEFAULT_SCENE_ID = "INS_PERIODIC"
DEFAULT_MAX_ROUNDS = MAX_DIALOG_ROUNDS

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

# Context pack sizes for different routes
# Controls final_k (top-N chunks) returned to LLM at each stage
# Higher values provide more context but increase latency and token usage
_REPLY_CONTEXT_K = int(os.getenv("AI_COACH_REPLY_CONTEXT_K", "5"))
_FINISH_CONTEXT_K = int(os.getenv("AI_COACH_FINISH_CONTEXT_K", "8"))


def _round_window(session: dict[str, Any]) -> tuple[int, int, int]:
    min_rounds = int(session.get("min_rounds", MIN_DIALOG_ROUNDS))
    target_rounds = int(session.get("target_rounds", DEFAULT_TARGET_ROUNDS))
    max_rounds = int(session.get("max_rounds", DEFAULT_MAX_ROUNDS))
    min_rounds = max(1, min(min_rounds, max_rounds))
    target_rounds = max(min_rounds, min(target_rounds, max_rounds))
    return min_rounds, target_rounds, max_rounds


def _should_finish_round(
    *,
    current_round: int,
    min_rounds: int,
    target_rounds: int,
    max_rounds: int,
    gap_intents: list[str],
) -> bool:
    if current_round >= max_rounds:
        return True
    if current_round < min_rounds:
        return False
    return current_round >= target_rounds and not gap_intents


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
            if _REDLINE_CROSS_CHECK_ENABLED:
                return _cross_check_red_lines(llm_result, answer, criterion)
            return llm_result
    # Rule scorer is sync (no I/O), call it directly — no need for to_thread
    return score_employee_answer(
        answer, reference_items, criterion=criterion, coverage=coverage
    )


# LLM 评委的最后一道程序化闸门:prompt(L4)和 schema 一致性校验都拦不住
# "回答里有红线词但 LLM 仍给高合规分"这类漏判——只有确定性的规则检测能兜底。
# 设 AI_COACH_REDLINE_CROSS_CHECK=0 可整体禁用(用于 A/B 对照)。
_RED_LINE_COMPLIANCE_CAP = 30
_REDLINE_CROSS_CHECK_ENABLED = os.getenv("AI_COACH_REDLINE_CROSS_CHECK", "1").lower() not in ("0", "false", "off")


def _cross_check_red_lines(
    score: dict[str, Any],
    answer: str,
    criterion: dict[str, Any] | None,
) -> dict[str, Any]:
    """Deterministic red-line cross-check applied to LLM scoring output.

    If the rule detector finds a severe compliance violation but the LLM gave
    compliance > cap, force the cap, recompute the weighted total, and merge
    the detected risk terms / weakness tag so the report stays consistent.
    """
    risk_hits, severe_violation = detect_compliance_violation(answer, criterion)
    if not severe_violation:
        return score

    dims = score.get("dimension_scores") or []
    compliance_dim = next((d for d in dims if d.get("key") == "compliance"), None)
    llm_compliance = int(compliance_dim.get("score", 0)) if compliance_dim else 0
    if compliance_dim is None or llm_compliance <= _RED_LINE_COMPLIANCE_CAP:
        return score  # LLM already penalized correctly

    logger.warning(
        "LLM scorer missed a severe red-line violation; capping compliance %s -> %s (hits=%s)",
        llm_compliance, _RED_LINE_COMPLIANCE_CAP, risk_hits,
    )
    compliance_dim["score"] = _RED_LINE_COMPLIANCE_CAP
    total = sum(int(d.get("score", 0)) * float(d.get("weight", 0)) for d in dims)
    score["total_score"] = int(max(0, min(100, round(total))))
    merged_risks = list(dict.fromkeys([*(score.get("risk_terms") or []), *risk_hits]))
    score["risk_terms"] = merged_risks
    if "合规红线" not in (score.get("weakness_tags") or []):
        score.setdefault("weakness_tags", []).append("合规红线")
    score["method"] = f"{score.get('method', '')}+redline_cap"
    return score


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
def _merge_llm_intents(
    covered_intents: list[str],
    llm_intents: list[str],
    keyword_intents: list[str] | None = None,
) -> list[str]:
    """Merge LLM-detected intents into the covered set.

    When LLM intents are available, they replace keyword intents for THIS turn
    (LLM precision ~0.79 vs keyword ~0.29). Previous turns' covered_intents
    are preserved unconditionally.
    """
    merged = set(covered_intents)
    merged.update(llm_intents)
    return sorted(merged)


# Intent to Chinese keywords mapping for repeat detection
INTENT_KEYWORDS_ZH = {
    "rate_concern": ["收益", "利率", "分红", "划算", "利息", "高", "多少"],
    "liquidity_concern": ["取出", "提前", "用钱", "灵活", "退保", "期限", "随时"],
    "safety_concern": ["安全", "风险", "亏", "本金", "保本", "保证", "承诺"],
    "procedure_question": ["怎么办", "流程", "材料", "办理", "手续", "带什么", "网点"],
    "rejection_or_hesitation": ["犹豫", "考虑", "想想", "家人", "商量", "再看看", "不急"],
    "compliance_sensitive": ["保证", "承诺", "写进合同", "绝对", "一定", "最高"],
}


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
    difficulty: str | None = None,
    auto_difficulty: bool = True,
) -> dict[str, Any]:
    task_detail = get_practice_task_detail(task_id) if task_id else None
    if task_detail:
        scene_id = task_detail.get("sceneId") or scene_id
        customer_id = customer_id or task_detail.get("customerId")
        difficulty = difficulty or task_detail.get("difficultyLevel")

    # Layer 3: 自适应难度 — 如果未指定 difficulty 且开启自动推荐，则根据历史成绩推荐
    difficulty_rec = None
    if not difficulty and not customer_id and auto_difficulty:
        difficulty_rec = recommend_difficulty(user_id=user_id, scene_id=scene_id)
        difficulty = difficulty_rec.recommended_difficulty

    profile = get_customer_profile(scene_id=scene_id, customer_id=customer_id, difficulty=difficulty)
    effective_scene_id = profile.get("scene_id") or scene_id
    # 用户读开场白的空窗期预热该画像的 prefix cache,降低首轮 reply 的 TTFT。
    if _CUSTOMER_LLM_PREFERENCE == "llm":
        warm_customer_prefix(profile, effective_scene_id)
    expected_intents = profile.get("expected_intents", [])
    round_policy = build_dialog_round_policy(
        direction=(task_detail or {}).get("direction"),
        difficulty=profile.get("difficulty_level") or difficulty,
        expected_intents=expected_intents,
        scene_id=effective_scene_id,
    )
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
        "scenario_id": effective_scene_id,
        "scene_id": effective_scene_id,
        "customer_id": profile.get("customer_id") or customer_id,
        "customer_type": profile.get("customer_type"),
        "difficulty_level": profile.get("difficulty_level") or difficulty or "中",
        "status": "running",
        "round": 1,
        "min_rounds": round_policy.min_rounds,
        "target_rounds": round_policy.target_rounds,
        "max_rounds": round_policy.max_rounds,
        "round_policy": {**round_policy.to_dict(), "effective_source": round_policy.source},
        "expected_intents": expected_intents,
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
    min_rounds, target_rounds, max_rounds = _round_window(session)
    current_round = int(session.get("round", 1))

    intent = analyze_customer_answer(employee_message)
    expected_intents = session.get("expected_intents", [])
    prev_covered = list(session.get("covered_intents", []))
    covered_intents = update_covered_intents(prev_covered, intent.get("intent_scores", {}))
    gap_intents = compute_intent_gap(expected_intents, covered_intents)
    finished = _should_finish_round(
        current_round=current_round,
        min_rounds=min_rounds,
        target_rounds=target_rounds,
        max_rounds=max_rounds,
        gap_intents=gap_intents,
    )

    retrieval: dict[str, Any] = {}
    next_question = None
    if not finished:
        retrieval = retrieve_marketing_knowledge(
            employee_message, route="customer", final_k=_REPLY_CONTEXT_K,
            scene_id=scene_id, focus_intents=gap_intents or None
        )
        retrieval_items = retrieval.get("items", [])
        customer_weakness = (session.get("weakness_profile") or {}).get("customer_prompt", "")
        cq_result = await _next_customer_question(
            session, employee_message, retrieval_items, intent, gap_intents, covered_intents,
            weakness_prompt=customer_weakness,
        )
        next_question = cq_result["follow_up"]
        llm_intents = cq_result.get("llm_intents")
        if llm_intents is not None:
            # LLM 为主：直接用 LLM 检测的意图更新 covered
            covered_intents = _merge_llm_intents(covered_intents, llm_intents)
            intent["llm_intents"] = llm_intents
            intent["intent_source"] = "llm"
        else:
            # LLM 不可用：keyword 兜底
            intent["intent_source"] = "keyword"
        gap_intents = compute_intent_gap(expected_intents, covered_intents)
        session["messages"].append({"role": "ai_customer", "content": next_question, "created_at": now_iso()})
        session["round"] = current_round + 1
    else:
        intent["intent_source"] = intent.get("intent_source", "keyword")

    session["last_intent"] = intent
    session["covered_intents"] = covered_intents
    session["intent_gap"] = gap_intents
    saved = manager.upsert_session(session)
    return {
        "session": saved,
        "ai_customer_message": next_question,
        "round": session.get("round", current_round),
        "min_rounds": min_rounds,
        "target_rounds": target_rounds,
        "max_rounds": max_rounds,
        "round_policy": session.get("round_policy", {}),
        "finished": finished,
        "intent": intent,
        "expected_intents": expected_intents,
        "covered_intents": covered_intents,
        "intent_gap": gap_intents,
        "retrieval": retrieval,
    }


async def reply_dialogue_stream(session_id: str, employee_message: str):
    """Async generator variant of reply_dialogue that yields SSE events.

    Yields dicts with "event" and "data" keys:
      - {"event": "meta", "data": {...}}       — intent/gap/round metadata (sent first)
      - {"event": "delta", "data": "..."}      — text chunk from LLM streaming
      - {"event": "done", "data": {...}}        — final message after stream completes
      - {"event": "fallback", "data": {...}}    — non-streaming fallback (template or LLM unavailable)
    """
    manager = get_memory_manager()
    session = manager.get_session(session_id)
    if not session:
        raise KeyError(f"session not found: {session_id}")
    session.setdefault("messages", []).append({"role": "employee", "content": employee_message, "created_at": now_iso()})
    scene_id = session.get("scene_id") or session.get("scenario_id")
    min_rounds, target_rounds, max_rounds = _round_window(session)
    current_round = int(session.get("round", 1))

    intent = analyze_customer_answer(employee_message)
    expected_intents = session.get("expected_intents", [])
    prev_covered = list(session.get("covered_intents", []))
    covered_intents = update_covered_intents(prev_covered, intent.get("intent_scores", {}))
    gap_intents = compute_intent_gap(expected_intents, covered_intents)
    finished = _should_finish_round(
        current_round=current_round,
        min_rounds=min_rounds,
        target_rounds=target_rounds,
        max_rounds=max_rounds,
        gap_intents=gap_intents,
    )

    yield {
        "event": "meta",
        "data": {
            "round": current_round,
            "totalRounds": max_rounds,
            "minRounds": min_rounds,
            "targetRounds": target_rounds,
            "maxRounds": max_rounds,
            "round_policy": session.get("round_policy", {}),
            "finished": finished,
            "intent": intent,
            "covered_intents": covered_intents,
            "intent_gap": gap_intents,
        },
    }

    if finished:
        session["last_intent"] = intent
        session["covered_intents"] = covered_intents
        session["intent_gap"] = gap_intents
        manager.upsert_session(session)
        yield {"event": "done", "data": {"ai_customer_message": None, "finished": True}}
        return

    retrieval = retrieve_marketing_knowledge(
        employee_message, route="customer", final_k=_REPLY_CONTEXT_K,
        scene_id=scene_id, focus_intents=gap_intents or None
    )
    retrieval_items = retrieval.get("items", [])
    customer_weakness = (session.get("weakness_profile") or {}).get("customer_prompt", "")

    if _CUSTOMER_LLM_PREFERENCE == "llm":
        profile = get_customer_profile(
            scene_id=session.get("scene_id") or session.get("scenario_id"),
            customer_id=session.get("customer_id"),
        ) or {}
        collected_text = []
        streamed = False
        async for chunk in generate_customer_question_stream(
            profile=profile,
            messages=session.get("messages", []),
            employee_message=employee_message,
            gap_intents=gap_intents,
            covered_intents=covered_intents,
            retrieval_items=retrieval_items,
            scene_id=scene_id,
            weakness_prompt=customer_weakness,
        ):
            streamed = True
            collected_text.append(chunk)

        if streamed and collected_text:
            from app.core.llm_customer import _parse_customer_response
            raw_text = "".join(collected_text)
            parsed = _parse_customer_response(raw_text)
            if parsed and parsed.get("follow_up"):
                full_text = parsed["follow_up"]
                llm_intents = parsed.get("intents") or []
                covered_intents = _merge_llm_intents(covered_intents, llm_intents)
                gap_intents = compute_intent_gap(expected_intents, covered_intents)
                intent["llm_intents"] = llm_intents
                intent["intent_source"] = "llm"
                session["messages"].append({"role": "ai_customer", "content": full_text, "created_at": now_iso()})
                session["round"] = current_round + 1
                session["last_intent"] = intent
                session["covered_intents"] = covered_intents
                session["intent_gap"] = gap_intents
                manager.upsert_session(session)
                yield {"event": "done", "data": {"ai_customer_message": full_text, "finished": False, "llm_intents": llm_intents}}
                return

    # LLM streaming failed or not enabled — fallback to non-streaming path
    cq_result = await _next_customer_question(
        session, employee_message, retrieval_items, intent, gap_intents, covered_intents,
        weakness_prompt=customer_weakness,
    )
    next_question = cq_result["follow_up"]
    llm_intents = cq_result.get("llm_intents")
    if llm_intents is not None:
        covered_intents = _merge_llm_intents(covered_intents, llm_intents)
        intent["llm_intents"] = llm_intents
        intent["intent_source"] = "llm"
    else:
        intent["intent_source"] = "keyword"
    gap_intents = compute_intent_gap(expected_intents, covered_intents)
    session["messages"].append({"role": "ai_customer", "content": next_question, "created_at": now_iso()})
    session["round"] = current_round + 1
    session["last_intent"] = intent
    session["covered_intents"] = covered_intents
    session["intent_gap"] = gap_intents
    manager.upsert_session(session)
    yield {"event": "fallback", "data": {"ai_customer_message": next_question, "finished": False}}


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
        final_k=_FINISH_CONTEXT_K,
        scene_id=scene_id,
        must_points=criterion.get("must_points") or None,
        answer_goal=criterion.get("answer_goal"),
        key_terms=criterion.get("key_terms") or None,
    )
    coverage = retrieval.get("retrieval_trace", {}).get("must_point_coverage") or {}
    if not coverage and criterion.get("must_points"):
        # Retrieval fell back (see fallback_reason) — must-point penalties are
        # disabled for this finish, so the score may run high. Surface it.
        logger.warning(
            "finish scoring without must_point coverage: session=%s scene=%s backend=%s reason=%s",
            session_id, scene_id,
            retrieval.get("retrieval_backend"), retrieval.get("fallback_reason"),
        )
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
) -> dict[str, Any]:
    """Pick the next customer follow-up (async).

    Returns {"follow_up": str, "llm_intents": list[str] | None}.
    llm_intents is the intent labels detected by the LLM for the employee's
    answer (piggybacked on the same call), or None if LLM was not used.
    """
    if _CUSTOMER_LLM_PREFERENCE == "llm":
        profile = get_customer_profile(
            scene_id=session.get("scene_id") or session.get("scenario_id"),
            customer_id=session.get("customer_id"),
        ) or {}
        llm_result = await generate_customer_question_with_llm(
            profile=profile,
            messages=session.get("messages", []),
            employee_message=employee_message,
            gap_intents=gap_intents,
            covered_intents=covered_intents,
            retrieval_items=retrieval_items,
            weakness_prompt=weakness_prompt,
        )
        if llm_result and llm_result.get("follow_up"):
            return {
                "follow_up": llm_result["follow_up"],
                "llm_intents": llm_result.get("intents") or [],
            }

    # Enhanced template fallback with gap-based selection
    # Priority: compliance_sensitive > gap intents > retrieval-based > general
    detected_labels = set(intent.get("intent_labels", []))

    # 1. Compliance-sensitive gets highest priority
    if "compliance_sensitive" in detected_labels:
        return {"follow_up": CUSTOMER_INTENT_PROBES["compliance_sensitive"], "llm_intents": None}

    # 2. Use gap-based intelligent selection (not just first match)
    # Prioritize gap intents that haven't been covered yet
    if gap_intents:
        # Try to find a gap intent with a specific probe
        for label in gap_intents:
            if label in CUSTOMER_INTENT_PROBES:
                # Check if we just asked about this (avoid immediate repetition)
                last_ai_msg = _get_last_ai_message(session.get("messages", []))
                if not _is_asking_about_same_topic(last_ai_msg, label):
                    return {"follow_up": CUSTOMER_INTENT_PROBES[label], "llm_intents": None}

    # 3. Gap-based followup even without explicit probe templates
    if gap_intents:
        followup = _generate_gap_based_followup(gap_intents, covered_intents, employee_message)
        if followup:
            return {"follow_up": followup, "llm_intents": None}

    # 4. Retrieval-aware fallback
    if retrieval_items:
        # Try to extract a relevant question from retrieved content
        for item in retrieval_items[:2]:
            content = item.get("content", "")
            if "怎么办" in content or "如何" in content:
                return {"follow_up": "你说的这些我大概明白了，那我现在适合办吗？需要怎么弄？", "llm_intents": None}
        return {"follow_up": "嗯，那具体怎么操作、需要什么材料？", "llm_intents": None}

    # 5. General fallback
    return {"follow_up": "我明白了，那你建议我下一步怎么做？", "llm_intents": None}


def _get_last_ai_message(messages: list[dict[str, Any]]) -> str:
    """Get the last AI customer message from the message history."""
    for msg in reversed(messages):
        if msg.get("role") == "ai_customer":
            return msg.get("content", "")
    return ""


def _is_asking_about_same_topic(last_ai_msg: str, intent_label: str) -> bool:
    """Check if the last AI message was already asking about the same intent.

    Avoids repetitive追问 on the same topic.

    Args:
        last_ai_msg: The last AI customer message
        intent_label: The intent label to check against

    Returns:
        True if the last message was already asking about this intent
    """
    if not last_ai_msg:
        return False

    # Get keywords for the target intent
    intent_keywords = INTENT_KEYWORDS_ZH.get(intent_label, [])
    if not intent_keywords:
        return False

    last_lower = last_ai_msg.lower()

    # Count how many keywords from the intent appear in the last message
    matched_keywords = [kw for kw in intent_keywords if kw in last_lower]

    # If multiple keywords match, we're likely asking about the same topic
    # Threshold: at least 2 keywords for intents with 3+ keywords, 1 for smaller sets
    if len(intent_keywords) >= 3:
        return len(matched_keywords) >= 2
    else:
        return len(matched_keywords) >= 1


def _generate_gap_based_followup(
    gap_intents: list[str],
    covered_intents: list[str],
    employee_message: str,
) -> str:
    """Generate an intelligent follow-up based on gap intents.

    Creates contextual follow-ups even when no template exists.
    """
    if not gap_intents:
        return ""

    # Map gap intents to contextual follow-up patterns
    gap_patterns = {
        "rate_concern": [
            "收益具体有多少呢？跟别的产品比怎么样？",
            "那我到底能拿多少收益，能说清楚点吗？",
        ],
        "liquidity_concern": [
            "那我中途要用钱怎么办？能随时取出来吗？",
            "这个灵活性怎么样？急用钱的话会不会亏？",
        ],
        "safety_concern": [
            "本金安全吗？有没有风险？",
            "这产品会不会亏？风险大不大？",
        ],
        "procedure_question": [
            "那怎么办、要带什么材料？",
            "具体什么流程、怎么操作？",
        ],
        "rejection_or_hesitation": [
            "我还是有点犹豫，为什么现在就要办？",
            "能不能再想想、和家人商量一下？",
        ],
        "compliance_sensitive": [
            "你刚才说的能不能写进合同、保证给我？",
            "那能不能给我保证、达不到怎么办？",
        ],
    }

    # Select follow-up for the first gap intent
    for label in gap_intents:
        if label in gap_patterns:
            patterns = gap_patterns[label]
            # Alternate between patterns for variety
            import hashlib
            hash_val = int(hashlib.md5(employee_message.encode()).hexdigest()[:8], 16)
            idx = hash_val % len(patterns)
            return patterns[idx]

    # Generic gap-based fallback
    return f"关于{'、'.join(gap_intents[:2])}这方面，能不能再说详细点？"


def _feedback(score: dict[str, Any]) -> str:
    weaknesses = score.get("weakness_tags") or []
    if weaknesses:
        return "建议下一轮重点补强：" + "、".join(weaknesses)
    return "整体表达较完整，下一轮可以继续加强需求确认和办理引导。"

