from __future__ import annotations

import math
from typing import Any

from app.core.chroma_vector_store import ChromaMarketingVectorStore, load_vector_manifest
from app.core.coverage import evaluate_coverage
from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.embedding_adapter import EmbeddingAdapter, get_embedding_adapter
from app.core.embedding_builder import load_marketing_chunks
from app.core.intent_labels import INTENT_KEYWORDS, INTENT_LABEL_DESCRIPTIONS, INTENT_LABELS
from app.core.text_cleaner import clean_text, lexical_similarity


TUTOR_HYDE_PATTERNS = {
    "liquidity": {
        "keywords": ["提前取", "急用", "流动", "不方便", "短期", "随时"],
        "ideal_answer": "理想回答应先认可客户对资金流动性的担忧，再询问资金使用时间，说明提前支取或期限选择的影响，并给出保留部分活期或选择较短期限的方案。",
        "scoring_focus": ["需求确认", "流动性说明", "期限匹配", "下一步办理引导"],
    },
    "rate": {
        "keywords": ["利率", "收益", "高一点", "别的银行", "比较", "划算"],
        "ideal_answer": "理想回答应认可客户关注收益，避免承诺最高收益，说明利率以系统或网点公示为准，并结合安全、便利、到期管理等因素做综合解释。",
        "scoring_focus": ["收益解释", "合规边界", "综合价值说明", "查询引导"],
    },
    "safety": {
        "keywords": ["风险", "亏", "本金", "安全吗", "保障", "保本"],
        "ideal_answer": "理想回答应明确产品风险和适配边界，禁止夸大或承诺，结合客户风险承受能力解释产品特点，并提示以正式材料和系统信息为准。",
        "scoring_focus": ["风险揭示", "适当性", "合规表达", "材料依据"],
    },
    "procedure": {
        "keywords": ["怎么办", "办理", "流程", "材料", "身份证", "查询"],
        "ideal_answer": "理想回答应说明办理步骤、所需材料、查询方式和下一步动作，并确认客户是否方便继续办理。",
        "scoring_focus": ["流程说明", "材料提示", "行动引导", "客户确认"],
    },
}


# Provisional rubric-coverage threshold; see note where it is used.
# Empirically separates genuinely-mentioned must_points (~0.40-0.60) from the
# Chinese semantic baseline of unmentioned ones (~0.25-0.35). Needs calibration.
TUTOR_MUST_POINT_THRESHOLD = 0.30


CUSTOMER_INTENT_EXPANSIONS = {
    "rate_concern": "客户可能继续追问利率、收益比较、是否比其他银行更划算。",
    "liquidity_concern": "客户可能继续追问提前支取、临时用钱、期限是否灵活。",
    "safety_concern": "客户可能继续追问本金安全、风险、是否会亏损。",
    "procedure_question": "客户可能继续追问办理流程、需要材料、如何查询和下一步怎么做。",
    "rejection_or_hesitation": "客户可能继续表达犹豫、想再考虑或和家人商量。",
    "compliance_sensitive": "客户可能追问保证、承诺、最高收益等合规敏感问题。",
}


def _normalize_scene_id(scene_id: str | None) -> str | None:
    if scene_id is None:
        return None
    value = clean_text(scene_id)
    if not value or value.lower() in {"null", "none", "undefined"}:
        return None
    return value


def _fallback_retrieve(query: str, route: str, top_k: int, scene_id: str | None = None) -> list[dict[str, Any]]:
    scene_id = _normalize_scene_id(scene_id)
    items: list[dict[str, Any]] = []
    for chunk in load_marketing_chunks():
        if scene_id and chunk.get("scene_id") != scene_id:
            continue
        text = "\n".join(
            str(part)
            for part in [
                chunk.get("customer_query", "") if route == "customer" else "",
                chunk.get("title", ""),
                chunk.get("customer_view_text", "") if route == "customer" else chunk.get("tutor_view_text", ""),
                chunk.get("content", ""),
            ]
            if part
        )
        score = lexical_similarity(query, text)
        if score > 0:
            items.append(
                {
                    "id": chunk.get("chunk_id"),
                    "score": score,
                    "distance": None,
                    "content": clean_text(text),
                    "metadata": {
                        "chunk_id": chunk.get("chunk_id"),
                        "scene_id": chunk.get("scene_id"),
                        "title": chunk.get("title"),
                        "knowledge_type": chunk.get("knowledge_type"),
                    },
                    "retrieval_source": "json_lexical_fallback",
                }
            )
    return sorted(items, key=lambda item: item["score"], reverse=True)[:top_k]


def _keyword_score(query: str, text: str) -> float:
    query_chars = {ch for ch in clean_text(query) if not ch.isspace()}
    if not query_chars:
        return 0.0
    text_value = clean_text(text)
    hits = sum(1 for ch in query_chars if ch in text_value)
    return round(hits / len(query_chars), 4)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return round(dot / (norm_a * norm_b), 4)


# Intent prototypes are static; cache their embeddings per adapter signature
# so we do not re-encode them on every customer reply.
_INTENT_PROTOTYPE_CACHE: dict[str, list[list[float]]] = {}


def _intent_prototype_embeddings(adapter: EmbeddingAdapter) -> list[list[float]]:
    signature = f"{adapter.info.active_backend}:{adapter.info.active_model}:{adapter.dimensions}"
    cached = _INTENT_PROTOTYPE_CACHE.get(signature)
    if cached is not None:
        return cached
    prototypes = [
        clean_text(
            f"{INTENT_LABEL_DESCRIPTIONS.get(label, '')} "
            f"{' '.join(INTENT_KEYWORDS.get(label, []))} "
            f"{CUSTOMER_INTENT_EXPANSIONS.get(label, '')}"
        )
        for label in INTENT_LABELS
    ]
    embeddings = adapter.embed_texts(prototypes)
    _INTENT_PROTOTYPE_CACHE[signature] = embeddings
    return embeddings


def _intent_semantic_scores(query: str, adapter: EmbeddingAdapter) -> dict[str, float]:
    query_embedding = adapter.embed_query(query)
    prototype_embeddings = _intent_prototype_embeddings(adapter)
    # Use raw cosine (clamped at 0). For normalized embeddings cosine is already
    # in a meaningful range; the previous (cos+1)/2 mapping compressed every label
    # into ~0.6-0.8 and destroyed discrimination between intents.
    return {
        label: max(0.0, round(_cosine(query_embedding, embedding), 4))
        for label, embedding in zip(INTENT_LABELS, prototype_embeddings)
    }


def _merge_ranked_items(candidate_groups: list[tuple[str, list[dict[str, Any]], float]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for source_name, items, weight in candidate_groups:
        for rank, item in enumerate(items):
            item_id = str(item.get("id") or item.get("metadata", {}).get("chunk_id") or item.get("content", "")[:80])
            base_score = float(item.get("score") or 0.0)
            rank_bonus = 1.0 / (rank + 1)
            weighted_score = weight * base_score + 0.03 * rank_bonus
            if item_id not in merged:
                merged[item_id] = {
                    **item,
                    "fusion_score": 0.0,
                    "fusion_sources": [],
                    "component_scores": {},
                }
            merged[item_id]["fusion_score"] += weighted_score
            merged[item_id]["fusion_sources"].append(source_name)
            merged[item_id]["component_scores"][source_name] = round(base_score, 4)
    return list(merged.values())


def _build_tutor_hyde_query(
    query: str,
    must_points: list[str] | None = None,
    answer_goal: str | None = None,
) -> dict[str, Any]:
    query_value = clean_text(query)

    # Preferred: anchor the hypothetical ideal answer on the scenario rubric
    # (criterion.must_points), NOT on the employee's own words. This lets the
    # retrieval surface evidence for points the employee OMITTED, so omissions
    # can be scored — the employee-keyword path could never retrieve those.
    if must_points:
        ideal_answers = [clean_text(point) for point in must_points if clean_text(point)]
        scoring_focus = ideal_answers[:]
        anchor = "rubric_must_points"
    else:
        ideal_answers = []
        scoring_focus = []
        for focus, config in TUTOR_HYDE_PATTERNS.items():
            if any(keyword in query_value for keyword in config["keywords"]):
                ideal_answers.append(config["ideal_answer"])
                scoring_focus.extend(config["scoring_focus"])
        if not ideal_answers:
            ideal_answers.append(
                "理想回答应先识别客户核心顾虑，再结合业务知识给出准确解释，避免承诺或编造，并给出清晰的下一步办理或查询引导。"
            )
            scoring_focus.extend(["需求识别", "业务解释", "合规边界", "下一步引导"])
        anchor = "employee_keyword_pattern"

    goal_line = clean_text(answer_goal) if answer_goal else "评估员工回答是否覆盖场景标准要点、合规边界并给出下一步引导。"
    expanded_query = "\n".join(
        [
            f"员工回答或客户问题：{query_value}",
            f"场景评分目标：{goal_line}",
            "导师评分检索目标：寻找标准话术、合规边界、业务解释、缺失点和改进建议。",
            "HyDE 假设理想回答（应覆盖的标准要点）：" + " ".join(ideal_answers),
            "评分关注点：" + "、".join(dict.fromkeys(scoring_focus)),
        ]
    )
    return {
        "original_query": query_value,
        "expanded_query": expanded_query,
        "anchor": anchor,
        "answer_goal": goal_line,
        "scoring_focus": list(dict.fromkeys(scoring_focus)),
        "hypothetical_answer": " ".join(ideal_answers),
    }


def _retrieve_tutor_hyde(
    store: ChromaMarketingVectorStore,
    collection_name: str,
    query: str,
    adapter: EmbeddingAdapter,
    top_k: int,
    scene_id: str | None,
    must_points: list[str] | None = None,
    answer_goal: str | None = None,
    key_terms: list[str] | None = None,
    fusion_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    w = fusion_weights or {}
    w_hyde = w.get("hyde_semantic", 0.72)
    w_orig = w.get("original_semantic", 0.23)
    w_kw = w.get("keyword_overlap", 0.05)

    hyde = _build_tutor_hyde_query(query, must_points=must_points, answer_goal=answer_goal)
    where = {"scene_id": scene_id} if scene_id else None
    hyde_items = store.query(collection_name, hyde["expanded_query"], adapter, top_k=max(top_k * 3, top_k), where=where)
    original_items = store.query(collection_name, query, adapter, top_k=max(top_k * 2, top_k), where=where)
    fused = _merge_ranked_items(
        [
            ("hyde_semantic", hyde_items, w_hyde),
            ("original_semantic", original_items, w_orig),
        ]
    )
    for item in fused:
        keyword = _keyword_score(query, item.get("content", ""))
        item["keyword_score"] = keyword
        item["score"] = round(item["fusion_score"] + w_kw * keyword, 4)
        item["retrieval_source"] = "tutor_hyde_chroma_fusion"
    ranked = sorted(fused, key=lambda item: item["score"], reverse=True)[:top_k]

    trace: dict[str, Any] = {
        "algorithm": "tutor_hyde_chroma_fusion_v1",
        "hyde": hyde,
        "weights": {
            "hyde_semantic": w_hyde,
            "original_semantic": w_orig,
            "keyword_overlap": w_kw,
        },
        "candidate_counts": {
            "hyde_semantic": len(hyde_items),
            "original_semantic": len(original_items),
            "fused": len(fused),
        },
    }
    # Rubric coverage: which must_points did the employee answer actually cover?
    # The missing ones are the omissions the tutor should penalize.
    # NOTE: 0.45 is a provisional threshold — Chinese semantic similarity has a
    # ~0.4 baseline floor, so this needs proper calibration against a labeled set
    # (tracked as a P1 follow-up). Until then treat coverage as directional.
    if must_points:
        dimensions = [
            {"id": f"mp_{idx}", "text": point, "keywords": key_terms or []}
            for idx, point in enumerate(must_points)
        ]
        trace["must_point_coverage"] = evaluate_coverage(dimensions, query, adapter, threshold=TUTOR_MUST_POINT_THRESHOLD)
    return {"items": ranked, "trace": trace}


# Intent selection thresholds (tuned for the keyword + semantic-prototype scale).
# - INTENT_ABS_FLOOR keeps clearly-irrelevant input (small flat scores) from
#   being tagged with any intent, so "今天天气不错" returns no labels.
# - INTENT_REL_RATIO keeps only labels close to the top score, so a single-intent
#   answer does not drag in 3 weak runner-ups.
INTENT_ABS_FLOOR = 0.20
INTENT_REL_RATIO = 0.75
INTENT_MAX_LABELS = 4


def _select_intent_labels(fused_scores: dict[str, float]) -> list[str]:
    ranked = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        return []
    top_score = ranked[0][1]
    cutoff = max(INTENT_ABS_FLOOR, INTENT_REL_RATIO * top_score)
    return [label for label, score in ranked if score >= cutoff][:INTENT_MAX_LABELS]


def _build_customer_query_plan(
    query: str,
    adapter: EmbeddingAdapter,
    focus_intents: list[str] | None = None,
    kw_weight: float = 0.55,
    sem_weight: float = 0.45,
) -> dict[str, Any]:
    understanding = analyze_customer_answer(query)
    keyword_scores = understanding.get("keyword_intent_scores", {})
    bert_scores = understanding.get("bert_mini_scores", {})
    bert_available = bool(understanding.get("bert_mini_available"))
    semantic_scores = _intent_semantic_scores(query, adapter)
    fused_scores: dict[str, float] = {}
    for label in set(keyword_scores) | set(semantic_scores):
        if bert_available:
            fused_scores[label] = round(
                0.60 * float(bert_scores.get(label, 0.0))
                + 0.25 * float(keyword_scores.get(label, 0.0))
                + 0.15 * semantic_scores.get(label, 0.0),
                4,
            )
        else:
            fused_scores[label] = round(kw_weight * float(keyword_scores.get(label, 0.0)) + sem_weight * semantic_scores.get(label, 0.0), 4)
    detected_labels = _select_intent_labels(fused_scores)

    # The follow-up should target the customer's UNADDRESSED concerns (the gap),
    # not what the employee already talked about. When the dialogue layer passes
    # focus_intents (= expected concerns minus covered), those drive the rewrite
    # and ranking; otherwise fall back to the intents detected in the answer.
    driving_labels = [label for label in (focus_intents or []) if label] or detected_labels
    expansions = [CUSTOMER_INTENT_EXPANSIONS[label] for label in driving_labels if label in CUSTOMER_INTENT_EXPANSIONS]
    rewritten_query = "\n".join(
        [
            f"员工回答：{clean_text(query)}",
            "客户下一轮追问目标：抓住员工尚未充分回应的客户顾虑，提出自然、尖锐但合规的追问。",
            "客户尚未被满足的顾虑：" + "、".join(driving_labels),
            "追问方向：" + " ".join(expansions),
        ]
    )
    return {
        "original_query": clean_text(query),
        "rewritten_query": rewritten_query,
        "intent_labels": driving_labels,
        "detected_intent_labels": detected_labels,
        "focus_intents": focus_intents or [],
        "keyword_intent_scores": keyword_scores,
        "semantic_intent_scores": semantic_scores,
        "bert_mini_intent_scores": bert_scores,
        "fused_intent_scores": fused_scores,
        "intent_expansions": expansions,
        "tagger": {
            "method": understanding["method"],
            "bert_mini_available": bert_available,
            "intent_source": "gap_focus" if (focus_intents or []) else "detected",
            "note": "Follow-up is driven by gap (expected customer concerns minus addressed) when the dialogue layer supplies focus_intents; otherwise by intents detected in the answer.",
        },
    }


def _intent_match_score(labels: list[str], text: str) -> float:
    if not labels:
        return 0.0
    text_value = clean_text(text)
    label_scores = []
    for label in labels:
        keywords = INTENT_KEYWORDS.get(label, [])
        if not keywords:
            continue
        hits = sum(1 for keyword in keywords if keyword in text_value)
        label_scores.append(hits / len(keywords))
    if not label_scores:
        return 0.0
    return round(sum(label_scores) / len(label_scores), 4)


def _retrieve_customer_intent_fusion(
    store: ChromaMarketingVectorStore,
    collection_name: str,
    query: str,
    adapter: EmbeddingAdapter,
    top_k: int,
    scene_id: str | None,
    focus_intents: list[str] | None = None,
    fusion_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    w = fusion_weights or {}
    w_intent_sem = w.get("intent_semantic", 0.58)
    w_orig_sem = w.get("original_semantic", 0.22)
    w_kw_recall = w.get("keyword_recall", 0.10)
    w_kw_overlap = w.get("keyword_overlap", 0.06)
    w_intent_match = w.get("intent_match", 0.04)

    plan = _build_customer_query_plan(query, adapter, focus_intents=focus_intents)
    where = {"scene_id": scene_id} if scene_id else None
    semantic_items = store.query(collection_name, plan["rewritten_query"], adapter, top_k=max(top_k * 3, top_k), where=where)
    original_items = store.query(collection_name, query, adapter, top_k=max(top_k * 2, top_k), where=where)
    keyword_items = _fallback_retrieve(query, route="customer", top_k=max(top_k * 2, top_k), scene_id=scene_id)
    fused = _merge_ranked_items(
        [
            ("intent_semantic", semantic_items, w_intent_sem),
            ("original_semantic", original_items, w_orig_sem),
            ("keyword_recall", keyword_items, w_kw_recall),
        ]
    )
    for item in fused:
        content = item.get("content", "")
        keyword = _keyword_score(query, content)
        intent = _intent_match_score(plan["intent_labels"], content)
        item["keyword_score"] = keyword
        item["intent_match_score"] = intent
        item["score"] = round(item["fusion_score"] + w_kw_overlap * keyword + w_intent_match * intent, 4)
        item["retrieval_source"] = "customer_intent_embedding_keyword_fusion"
    ranked = sorted(fused, key=lambda item: item["score"], reverse=True)[:top_k]
    return {
        "items": ranked,
        "trace": {
            "algorithm": "customer_intent_embedding_keyword_fusion_v1",
            "query_plan": plan,
            "weights": {
                "intent_semantic": w_intent_sem,
                "original_semantic": w_orig_sem,
                "keyword_recall": w_kw_recall,
                "keyword_overlap": w_kw_overlap,
                "intent_match": w_intent_match,
            },
            "candidate_counts": {
                "intent_semantic": len(semantic_items),
                "original_semantic": len(original_items),
                "keyword_recall": len(keyword_items),
                "fused": len(fused),
            },
        },
    }


def retrieve_marketing_knowledge(
    query: str,
    route: str = "tutor",
    top_k: int = 5,
    scene_id: str | None = None,
    focus_intents: list[str] | None = None,
    must_points: list[str] | None = None,
    answer_goal: str | None = None,
    key_terms: list[str] | None = None,
    fusion_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    route = "customer" if route == "customer" else "tutor"
    scene_id = _normalize_scene_id(scene_id)
    manifest = load_vector_manifest()
    if manifest:
        try:
            adapter_info = manifest.get("embedding_adapter") or {}
            adapter = get_embedding_adapter(
                backend=adapter_info.get("active_backend") or manifest.get("embedding_backend"),
                model_name=adapter_info.get("active_model") or manifest.get("embedding_model"),
                dimensions=manifest.get("dimensions"),
                allow_fallback=True,
            )
            collection_name = manifest["collections"][route]["name"]
            store = ChromaMarketingVectorStore()
            if route == "customer":
                result = _retrieve_customer_intent_fusion(
                    store, collection_name, query, adapter, top_k, scene_id,
                    focus_intents=focus_intents, fusion_weights=fusion_weights,
                )
            else:
                result = _retrieve_tutor_hyde(
                    store, collection_name, query, adapter, top_k, scene_id,
                    must_points=must_points, answer_goal=answer_goal, key_terms=key_terms,
                    fusion_weights=fusion_weights,
                )
            return {
                "query": query,
                "route": route,
                "items": result["items"],
                "retrieval_backend": "chroma",
                "retrieval_algorithm": result["trace"]["algorithm"],
                "retrieval_trace": result["trace"],
                "embedding_adapter": adapter.describe(),
            }
        except Exception as exc:
            fallback_items = _fallback_retrieve(query, route=route, top_k=top_k, scene_id=scene_id)
            return {
                "query": query,
                "route": route,
                "items": fallback_items,
                "retrieval_backend": "json_lexical_fallback",
                "retrieval_algorithm": f"{route}_lexical_fallback",
                "fallback_reason": str(exc)[:500],
            }
    return {
        "query": query,
        "route": route,
        "items": _fallback_retrieve(query, route=route, top_k=top_k, scene_id=scene_id),
        "retrieval_backend": "json_lexical_fallback",
        "retrieval_algorithm": f"{route}_lexical_fallback",
        "fallback_reason": "vector manifest not found",
    }
