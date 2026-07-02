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


def _compress_must_points(must_points: list[str], max_length: int = 200) -> list[str]:
    """压缩must_points，避免query过长导致embedding失焦。

    策略：
    1. 如果总长度在限制内，保持原样
    2. 否则提取每个must_point的关键词（名词、动词）
    3. 保留前2个完整句子+其余的关键词摘要
    """
    if not must_points:
        return must_points

    total_length = sum(len(point) for point in must_points)
    if total_length <= max_length:
        return must_points

    # 提取关键词的简单策略：取每个句子的前半部分（通常包含主谓核心）
    compressed = []
    remaining = max_length

    # 前2个完整句子
    for i, point in enumerate(must_points[:2]):
        if len(point) <= remaining:
            compressed.append(point)
            remaining -= len(point)
        else:
            compressed.append(point[:remaining] + "...")
            remaining = 0
            break

    # 其余用关键词摘要
    if len(must_points) > 2 and remaining > 20:
        keywords = []
        for point in must_points[2:]:
            # 取每个句子的前15-20个字符作为关键词摘要
            kw = point[:20].strip()
            if kw:
                keywords.append(kw)

        if keywords and remaining > 20:
            summary = "关键词：" + "、".join(keywords[:3])
            if len(summary) <= remaining:
                compressed.append(summary)

    return compressed


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
        # 压缩must_points避免query过长
        compressed_points = _compress_must_points(must_points, max_length=150)
        ideal_answers = [clean_text(point) for point in compressed_points if clean_text(point)]
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
        "must_points_compressed": len(must_points) > 0 if must_points else False,
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
    w_hyde = w.get("hyde_semantic", 0.55)
    w_orig = w.get("original_semantic", 0.20)
    w_kw = w.get("keyword_overlap", 0.15)
    w_type = w.get("type_boost", 0.20)  # 类型匹配增强权重（提高到0.20以增强类型区分）

    hyde = _build_tutor_hyde_query(query, must_points=must_points, answer_goal=answer_goal)
    where = {"scene_id": scene_id} if scene_id else None

    # 推断查询类型偏好
    query_type_hint = _infer_query_type_preference(query, must_points)

    # 扩大召回候选池
    hyde_items = store.query(collection_name, hyde["expanded_query"], adapter, top_k=max(top_k * 8, 40), where=where)
    original_items = store.query(collection_name, query, adapter, top_k=max(top_k * 6, 30), where=where)

    # 类型感知融合：优先匹配的types获得更高权重
    fused = _merge_ranked_items_with_type_boost(
        [("hyde_semantic", hyde_items, w_hyde),
         ("original_semantic", original_items, w_orig)],
        query_type_hint,
        w_type
    )

    for item in fused:
        keyword = _keyword_score(query, item.get("content", ""))
        item["keyword_score"] = keyword
        # 使用fusion_score（包含type boost）作为基础分数
        item["score"] = round(item.get("fusion_score", item.get("score", 0)) + w_kw * keyword, 4)
        item["retrieval_source"] = "tutor_hyde_chroma_fusion_v4"

    # 场景内优先重排：同场景chunk给予额外加分
    for item in fused:
        if scene_id and item.get("metadata", {}).get("scene_id") == scene_id:
            item["score"] = round(item["score"] + 0.08, 4)

    ranked = sorted(fused, key=lambda item: item["score"], reverse=True)[:top_k]

    trace: dict[str, Any] = {
        "algorithm": "tutor_hyde_chroma_fusion_v4",
        "hyde": hyde,
        "inferred_type": query_type_hint,
        "weights": {
            "hyde_semantic": w_hyde,
            "original_semantic": w_orig,
            "keyword_overlap": w_kw,
            "type_boost": w_type,
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

    # Query压缩：避免过长的query影响embedding质量
    query_clean = clean_text(query)
    if len(query_clean) > 100:
        query_clean = query_clean[:100] + "..."  # 保留前100字符即可

    rewritten_query = "\n".join(
        [
            f"员工回答：{query_clean}",
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
    w_intent_sem = w.get("intent_semantic", 0.50)
    w_orig_sem = w.get("original_semantic", 0.20)
    w_kw_recall = w.get("keyword_recall", 0.15)
    w_kw_overlap = w.get("keyword_overlap", 0.10)
    w_intent_match = w.get("intent_match", 0.05)

    plan = _build_customer_query_plan(query, adapter, focus_intents=focus_intents)
    where = {"scene_id": scene_id} if scene_id else None
    # 扩大召回候选池：customer route的gold数量通常更多
    semantic_items = store.query(collection_name, plan["rewritten_query"], adapter, top_k=max(top_k * 8, 40), where=where)
    original_items = store.query(collection_name, query, adapter, top_k=max(top_k * 5, 25), where=where)
    keyword_items = _fallback_retrieve(query, route="customer", top_k=max(top_k * 3, 15), scene_id=scene_id)
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
        item["retrieval_source"] = "customer_intent_embedding_keyword_fusion_v2"
    # 场景内优先重排：同场景chunk给予额外加分
    for item in fused:
        if scene_id and item.get("metadata", {}).get("scene_id") == scene_id:
            item["score"] = round(item["score"] + 0.05, 4)
    ranked = sorted(fused, key=lambda item: item["score"], reverse=True)[:top_k]
    return {
        "items": ranked,
        "trace": {
            "algorithm": "customer_intent_embedding_keyword_fusion_v2",
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


def _get_adaptive_top_k(
    base_top_k: int,
    route: str,
    scene_id: str | None = None,
    query: str | None = None,
    must_points: list[str] | None = None,
) -> int:
    """根据场景和查询特征动态调整top_k。

    策略：
    - tutor route且有must_points时：需要检索更多候选（因为gold数量通常较多）
    - customer route：适中即可
    - query过长时：增大候选池
    """
    adaptive_k = base_top_k

    # route基础倍数
    route_multiplier = {"tutor": 2.0, "customer": 1.5}.get(route, 1.5)
    adaptive_k = max(adaptive_k, int(base_top_k * route_multiplier))

    # must_points数量影响
    if must_points and len(must_points) > 3:
        adaptive_k = max(adaptive_k, int(base_top_k * 3))

    # query长度影响
    if query and len(clean_text(query)) > 150:
        adaptive_k = max(adaptive_k, int(base_top_k * 2.5))

    # 特定场景的gold数量通常较多，给予更高倍数
    high_gold_scenes = {
        "INS_PERIODIC", "INS_GENERAL", "FUND_GENERAL",
        "WM_ASSET", "INS_DIVIDEND",
    }
    if scene_id and scene_id in high_gold_scenes:
        adaptive_k = max(adaptive_k, int(base_top_k * 3))

    return min(adaptive_k, 20)  # 最大限制在20


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

    # 应用智能top_k
    adaptive_top_k = _get_adaptive_top_k(top_k, route, scene_id, query, must_points)

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
                    store, collection_name, query, adapter, adaptive_top_k, scene_id,
                    focus_intents=focus_intents, fusion_weights=fusion_weights,
                )
            else:
                result = _retrieve_tutor_hyde(
                    store, collection_name, query, adapter, adaptive_top_k, scene_id,
                    must_points=must_points, answer_goal=answer_goal, key_terms=key_terms,
                    fusion_weights=fusion_weights,
                )
            return {
                "query": query,
                "route": route,
                "items": result["items"][:top_k],  # 返回用户请求的top_k数量
                "retrieval_backend": "chroma",
                "retrieval_algorithm": result["trace"]["algorithm"],
                "retrieval_trace": result["trace"],
                "embedding_adapter": adapter.describe(),
                "adaptive_top_k": adaptive_top_k,  # 记录实际使用的top_k
                "user_requested_top_k": top_k,
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
                "adaptive_top_k": top_k,
                "user_requested_top_k": top_k,
            }
    return {
        "query": query,
        "route": route,
        "items": _fallback_retrieve(query, route=route, top_k=top_k, scene_id=scene_id),
        "retrieval_backend": "json_lexical_fallback",
        "retrieval_algorithm": f"{route}_lexical_fallback",
        "fallback_reason": "vector manifest not found",
        "adaptive_top_k": top_k,
        "user_requested_top_k": top_k,
    }


def _infer_query_type_preference(query: str, must_points: list[str] | None = None) -> str | None:
    """推断查询的knowledge_type偏好。

    处理两种查询风格：
    1. 自然查询：直接包含类型关键词
    2. 标准查询（评估用）：包含评分标准和期望描述

    使用加权评分而非"先到先得"，优先选择关键词匹配最多的类型。
    """
    query_lower = clean_text(query).lower()

    # 扩展的关键词集，同时支持自然查询和标准查询风格
    # 高优先级关键词（权重2x）：更能代表该类型的特征词
    type_keywords = {
        "raw_script": {
            "high_priority": ["客户说", "员工回答", "完整话术", "示范话术", "话术中的"],
            "normal": ["围绕客户需求", "展开沟通", "覆盖话术", "核心业务信息",
                      "下一步建议", "明确但不强迫", "合规表达", "避免绝对化",
                      "示范", "沟通", "表达"]
        },
        "product_intro": {
            "high_priority": ["产品介绍", "产品特点", "核心功能", "说明产品", "说明服务"],
            "normal": ["核心特点", "期限、收益", "费用、资产", "适用条件", "关键信息",
                      "风险、限制", "不确定性", "适配性", "正式产品说明", "合同或业务规则"]
        },
        "sales_process": {
            "high_priority": ["办理流程", "销售流程", "办理步骤", "推进顺序"],
            "normal": ["办理", "流程", "步骤", "材料", "需求了解、产品说明", "确认办理",
                      "关键材料", "自主决策", "确认客户需求"]
        },
        "objection_handling": {
            "high_priority": ["异议处理", "回应客户", "认可或回应", "澄清客户"],
            "normal": ["异议", "顾虑", "担忧", "结合产品规则", "业务事实",
                      "可选择的后续方案", "避免绝对化"]
        },
        "phone_invitation": {
            "high_priority": ["邀约", "电话邀约", "电话", "邀请", "下一步邀约", "办理动作"],
            "normal": ["联系", "网点", "确认客户身份", "沟通场景", "联系原因", "服务背景",
                      "夸大收益", "承诺结果"]
        },
        "compliance_note": {
            "high_priority": ["合规提示", "合规", "不当承诺", "绝对化收益"],
            "normal": ["风险", "提示", "注意", "误导性表达", "替代表达",
                      "产品风险", "规则边界", "识别", "审慎"]
        },
    }

    def _type_score(text: str, keywords: dict) -> float:
        """计算类型匹配分数：高优先级关键词权重2x"""
        score = 0.0
        for kw in keywords.get("high_priority", []):
            if kw in text:
                score += 2.0
        for kw in keywords.get("normal", []):
            if kw in text:
                score += 1.0
        return score

    # 优先检查 must_points（通常包含更明确的类型信号）
    if must_points:
        points_text = " ".join(clean_text(p) for p in must_points)
        best_type = None
        best_score = 0.0
        for type_name, keywords in type_keywords.items():
            score = _type_score(points_text, keywords)
            if score > best_score:
                best_score = score
                best_type = type_name
        if best_type and best_score > 0:
            return best_type

    # 检查主查询 - 选择分数最高的类型
    best_type = None
    best_score = 0.0
    for type_name, keywords in type_keywords.items():
        score = _type_score(query_lower, keywords)
        if score > best_score:
            best_score = score
            best_type = type_name

    return best_type if best_score > 0 else None


def _are_related_types(type1: str, type2: str) -> bool:
    """判断两个knowledge_type是否相关。"""
    type_groups = {
        "script": {"raw_script", "product_intro", "objection_handling"},
        "process": {"sales_process", "phone_invitation"},
        "compliance": {"compliance_note", "objection_handling"},
    }
    for group in type_groups.values():
        if type1 in group and type2 in group:
            return True
    return False


def _merge_ranked_items_with_type_boost(
    candidate_groups: list[tuple[str, list[dict[str, Any]], float]],
    query_type_hint: str | None,
    type_boost_weight: float = 0.10,
) -> list[dict[str, Any]]:
    """带类型感知的融合排序。

    对于类型匹配的chunk给予加成，对于类型不匹配的chunk给予惩罚。
    """
    merged: dict[str, dict[str, Any]] = {}
    for source_name, items, weight in candidate_groups:
        for rank, item in enumerate(items):
            item_id = str(item.get("id") or item.get("metadata", {}).get("chunk_id") or item.get("content", "")[:80])
            base_score = float(item.get("score") or 0)
            rank_bonus = 1.0 / (rank + 1)
            weighted_score = weight * base_score + 0.03 * rank_bonus

            # 类型匹配加成/惩罚
            type_boost = 0.0
            if query_type_hint:
                chunk_type = item.get("metadata", {}).get("knowledge_type", "")
                if chunk_type == query_type_hint:
                    # 完全匹配：加成
                    type_boost = type_boost_weight
                elif _are_related_types(chunk_type, query_type_hint):
                    # 相关类型：部分加成
                    type_boost = type_boost_weight * 0.3
                else:
                    # 不相关类型：轻微惩罚
                    type_boost = -type_boost_weight * 0.5

            weighted_score += type_boost

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
