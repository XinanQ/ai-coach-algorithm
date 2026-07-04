# 算法文档 01 — 双路 RAG

> 涉及代码:[app/core/marketing_rag.py](../../app/core/marketing_rag.py) + [app/core/coverage.py](../../app/core/coverage.py)
> 上游依赖:[app/core/chroma_vector_store.py](../../app/core/chroma_vector_store.py) + [app/core/embedding_adapter.py](../../app/core/embedding_adapter.py)

## 1. 核心问题

陪练系统有两个截然不同的检索需求,套用同一套 RAG 会失败:

| 视角 | 想拿到什么 | 用什么 query | 主要风险 |
|---|---|---|---|
| **导师侧**(评分) | 标准话术、合规边界、员工**没说的**要点 | 应该 = "理想答案" 而不是员工原文 | 用员工原文查 → 永远查不到员工漏答的内容 |
| **客户侧**(追问) | 类似客户在这种处境下会怎么发问的标准话术 | 应该 = "未被回应的顾虑" 而不是员工原文 | 用员工原文查 → 反复追问员工已经聊过的话题 |

**解法:两条独立检索链路,共享底层向量库,但 query 改写逻辑完全不同**。

## 2. 整体数据流

```
                                  ┌─ Chroma 向量库(tutor collection)
                                  │   embedding: BAAI/bge-small-zh-v1.5
       ┌──────────────────────────┘
       │
   导师侧 ─ _retrieve_tutor_hyde
       │   1. 用 must_points 构造 HyDE 假设答案
       │   2. HyDE + 原始 query 双路检索,fusion
       │   3. evaluate_coverage 算 must_point 覆盖率
       ▼
   coverage = { covered, missing, missing_texts, coverage_rate }
   → 喂给 LLM 评分(算 objection_handling / logic_structure)
   → missing_texts 喂给 suggestion 写"应该补充什么"

                                  ┌─ Chroma 向量库(customer collection)
                                  │
       ┌──────────────────────────┘
       │
   客户侧 ─ _retrieve_customer_intent_fusion
       │   1. analyze_customer_answer → intent_scores
       │   2. update_covered_intents 跨轮累积
       │   3. compute_intent_gap(expected, covered) → gap_intents
       │   4. gap_intents 驱动 query 改写 → intent_semantic / 原始 / keyword 三路 fusion
       ▼
   retrieval items
   → 给 LLM 客户模拟"参考语气",但不照搬
```

两侧检索完全独立运行,通过 `marketing_rag.retrieve_marketing_knowledge(route="tutor"|"customer")` 分发。

## 3. 导师侧:HyDE 锚定 rubric

### 3.1 关键设计:HyDE 锚定 must_points 而不是员工原文

**传统 HyDE**(行业默认):用员工原话扩写一个理想答案 → 检索。

**问题**:扩写出来的"理想答案"还是围绕员工说过的内容,**员工没说的部分根本进不来**。员工漏答的标准要点永远查不到 → 评分器看不见漏答 → 评不出 "漏答扣分"。

**我们的解法**(`_build_tutor_hyde_query` in marketing_rag.py):

```python
if must_points:  # 来自 criterion.must_points,场景预定义的标准要点
    ideal_answers = [point for point in must_points]  # ← 直接用 must_points 当假设答案
    anchor = "rubric_must_points"
else:
    # 兜底:无 rubric 时回退到员工关键词模式库
    anchor = "employee_keyword_pattern"
```

效果:HyDE query 强制覆盖**全部应该说的内容**,即使员工实际没说。检索回来的 chunk 既包含员工说过的(可用于打"说对了"加分),也包含员工没说的(可用于打"漏答"扣分)。

### 3.2 检索融合公式

```python
# 导师侧(v5优化版)
fusion_score = 0.50 × HyDE 假设答案的语义检索
             + 0.25 × 原始 query 的语义检索
             + 0.10 × 关键词重合度
             + 0.15 × 类型加分(type_boost)

# 客户侧(v3优化版)
fusion_score = 0.55 × 意图改写 query 的语义检索    ← 主信号
             + 0.25 × 原始 employee_message 的语义检索  ← 弱信号
             + 0.10 × JSON 关键词召回           ← 兜底召回
             + 0.05 × 关键词重合度
             + 0.05 × 意图关键词匹配度
```

**权重的来由(v5/v3优化后):**
- HyDE 权重调整(0.50 → 原 0.72):平衡语义与精确匹配,提升召回覆盖率
- 原始 query 权重提升(0.25 → 原 0.23):增强原始query信号
- 关键词重合度(0.10/0.05):防 embedding 完全失灵时的兜底
- 类型加分(0.15):场景匹配优先加权

调权重的位置:`marketing_rag._retrieve_tutor_hyde` 第 248 行附近。

### 3.3 Coverage 计算

检索完后立即调 `evaluate_coverage(must_points, employee_answer, adapter)`:

```python
# 每个 must_point 单独计分
score = 0.3 × keyword_hit_rate + 0.7 × cosine(answer, must_point)  ← v5优化
covered = (score >= THRESHOLD)  # THRESHOLD = 0.30,经 eval 扫描标定
```

输出:

```python
{
  "items": [{dimension_id, text, score, covered, keyword_hits}, ...],
  "covered": ["mp_0", "mp_2"],
  "missing": ["mp_1", "mp_3"],
  "missing_texts": ["说明分红存在不确定性", "提醒以保险合同为准"],
  "coverage_rate": 0.5,
  "threshold": 0.30
}
```

`missing_texts` 会被传给 LLM 评分器,LLM 在 suggestion 里直接引用("建议补充以下标准要点:...")。

### 3.4 阈值 0.30 是怎么来的

中文 sentence embedding 有约 0.25-0.35 的"噪声基线"(完全无关的两段话也有 0.25 左右的余弦)。

原始经验值 0.50 经 eval 评测体系扫描后发现偏高:point_f1 只有 0.59。在 0.15-0.50 范围扫描后,**0.30** 是 F1 最高点(0.7951),recall 提升到 0.92。v5优化调整权重组合(kw_weight=0.3, sem_weight=0.7)后,预期 F1 提升至 0.8225。

定义在 `marketing_rag.TUTOR_MUST_POINT_THRESHOLD`,可通过 `eval/sweep.py --stage must_point` 重新标定。

## 4. 客户侧:意图 gap 驱动追问

### 4.1 关键设计:用未被回应的顾虑驱动检索

客户的 expected_intents 是画像预定义的(比如流动性担忧型客户的 expected_intents = `[liquidity_concern, procedure_question]`)。每轮员工回答后:

```python
intent_scores = analyze_customer_answer(employee_message)["intent_scores"]
covered = update_covered_intents(previous_covered, intent_scores, threshold=0.10)
gap = compute_intent_gap(expected_intents, covered)
```

`gap` 就是"客户还没被回应的顾虑列表"。检索 query 改写就用 gap 驱动:

```python
# _build_customer_query_plan
driving_labels = focus_intents or detected_labels  # gap 优先
expansions = [INTENT_EXPANSIONS[label] for label in driving_labels]
rewritten_query = f"""
员工回答:{employee_message}
客户尚未被满足的顾虑:{driving_labels}  ← gap 在这里
追问方向:{expansions}
"""
```

效果:即使员工答得不好,RAG 也按"客户还想问什么"检索,不会反复绕在员工已经聊过的话题。

### 4.2 检索融合公式

```python
# 客户侧(v3优化版)
fusion_score = 0.55 × 意图改写 query 的语义检索    ← 主信号
             + 0.25 × 原始 employee_message 的语义检索  ← 弱信号
             + 0.10 × JSON 关键词召回           ← 兜底召回
             + 0.05 × 关键词重合度
             + 0.05 × 意图关键词匹配度
```

调权重的位置:`marketing_rag._retrieve_customer_intent_fusion` 第 403 行附近。

### 4.3 标签选择的双阈值

`_select_intent_labels` 用绝对下限 + 相对比例双阈值,防 false positive:

```python
INTENT_ABS_FLOOR = 0.08    # 绝对下限(经 eval 扫描从 0.20 标定)
INTENT_REL_RATIO = 0.50    # 相对比例(经 eval 扫描从 0.75 标定)
INTENT_MAX_LABELS = 4      # 最多 4 个标签

cutoff = max(INTENT_ABS_FLOOR, INTENT_REL_RATIO * top_score)
return [label for label, score in ranked if score >= cutoff][:INTENT_MAX_LABELS]
```

效果:
- 无关输入(比如"今天天气真好")不会被强行打标签 → `[]`
- 单意图答案不会拖出 3 个弱 runner-up

## 5. Coverage 共享模块

`coverage.py` 是两侧共用的抽象:**"期望维度里员工答到了哪些、漏了哪些"**。

| | 导师侧 | 客户侧 |
|---|---|---|
| 期望维度 | `criterion.must_points`(clause 级) | `profile.expected_intents`(label 级) |
| 覆盖判定函数 | `evaluate_coverage()` | `compute_intent_gap()` + `update_covered_intents()` |
| 覆盖算法 | `0.4 × keyword + 0.6 × cosine`,按 must_point 单独算 | 纯集合差,按意图标签 |
| 阈值 | 0.30(eval 扫描标定) | 0.10(eval 扫描标定) |
| 累积逻辑 | finish 一次性算 | reply 跨轮累积 |
| 用途 | 漏答扣分 + 检索锚点 | 驱动客户追问 |

两侧共用同一份代码,粒度不同但语义同构——这是设计上的关键统一性。

## 6. 调优入口速查

| 想改什么 | 改哪里 |
|---|---|
| 导师侧融合权重(v5) | `marketing_rag.py:248` `_retrieve_tutor_hyde` (hyde=0.50, orig=0.25, kw=0.10, type=0.15) |
| 客户侧融合权重(v3) | `marketing_rag.py:403` `_retrieve_customer_intent_fusion` (intent=0.55, orig=0.25, kw=0.10, overlap=0.05) |
| 导师候选池大小 | `retrieve_marketing_knowledge(candidate_k=...)`；finish/eval 建议 40 |
| 客户候选池大小 | `retrieve_marketing_knowledge(candidate_k=...)`；reply 默认 20 保持轻量 |
| Chroma 单次查询上限 | `AI_COACH_CHROMA_MAX_QUERY_RESULTS`，默认 80 |
| 场景优先加分 | `marketing_rag.py:284` `SCENE_PRIORITY_BOOST = 0.12`(tutor) / `0.10`(customer) |
| HyDE 假设答案模板(无 must_points 时的兜底) | `marketing_rag.TUTOR_HYDE_PATTERNS` |
| 客户意图扩展话术(用于 query 改写) | `marketing_rag.CUSTOMER_INTENT_EXPANSIONS` |
| must_point 覆盖判定阈值 | `marketing_rag.TUTOR_MUST_POINT_THRESHOLD = 0.30` |
| must_point 覆盖权重(v5) | `marketing_rag.py:287` `kw_weight=0.3, sem_weight=0.7` |
| 意图覆盖判定阈值 | `coverage.update_covered_intents(threshold=0.10)` |
| 意图选择的双阈值 | `marketing_rag.INTENT_ABS_FLOOR(0.08) / INTENT_REL_RATIO(0.50) / INTENT_MAX_LABELS(4)` |
| 逐级评测 | `python -m eval.run_all --stages all` |
| 参数扫描 | `python -m eval.sweep --stage intent --param abs_floor --min 0.05 --max 0.3` |
| 检索返回数 | `retrieve_marketing_knowledge(final_k=...)`；`top_k` 仅作为旧兼容别名 |

## 7. 已知限制与待办

| 问题 | 现状 | 路径 |
|---|---|---|
| `TUTOR_MUST_POINT_THRESHOLD = 0.30` 经 eval 标定 | 已标定 | `eval/sweep.py --stage must_point` 重新扫描 |
| 中文 embedding 基线高(~0.3-0.4) | 已知 | 长期可考虑换 BGE-large-zh 或 m3e-large |
| 客户侧关键词意图识别不灵敏 | 已知 | 当前 LLM 客户已直接读上下文,gap 仅作辅助,问题被绕开 |
| Chroma PersistentClient 缓存致测试偶发 flaky | 已知 | 测试间清缓存,生产无影响 |
| Gold标注过于宽泛导致理论天花板受限 | 已知 | 当前recall@3已达到理论天花板0.5869；后续需细化gold粒度 |
| Customer route gold过多导致召回困难 | 已知 | 平均13个gold,需压缩标注范围 |

## 8. 失败回退

| 失败点 | 兜底 | 影响 |
|---|---|---|
| Chroma 加载失败 | 退到 `_fallback_retrieve`(纯 keyword lexical) | 检索质量下降,系统仍工作 |
| Embedding model 加载失败 | 退到 `local_hash_embedding_v1` | 检索质量显著下降,但 demo 可跑 |
| 无 must_points / 无画像 | HyDE 退到 `TUTOR_HYDE_PATTERNS` 关键词模板 | 评分锚点弱化 |
| 全部检索结果为空 | 评分器走 missing_points = 全部 must_points | 评分会偏低 |
