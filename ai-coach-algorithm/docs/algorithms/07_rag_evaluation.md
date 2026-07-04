# 算法文档 07 — RAG 逐级评测体系

> 涉及代码:[eval/](../../eval/) 目录 + [app/core/marketing_rag.py](../../app/core/marketing_rag.py)(权重参数化)
> 数据:[data/eval/](../../data/eval/) + [data/intent_eval_gold.jsonl](../../data/intent_eval_gold.jsonl)

## 1. 核心问题

RAG 链路上每个环节的误差会级联放大。即使每步准确率 90%,五步连乘只剩 0.9⁵ = 59%。系统需要:

1. 给每个环节**单独打分**,定位哪个环节最拉胯
2. 支持**参数扫描**,用数据而不是直觉调参
3. **一键出报告**,每次改参数后对比效果

## 2. 评测的 4 个环节

```
员工回答 → ① 意图检测 → ② Gap计算 → ③ 知识检索 → ④ 要点覆盖 → LLM生成
```

| # | 环节 | 路由 | Gold 数据 | 核心指标 | 当前值 |
|---|------|------|----------|---------|--------|
| 1 | 意图检测 | 客户路 | 193 行(人工标注) | micro_f1 | **0.7576** |
| 2 | Gap 计算 | 客户路 | 104 行(半自动) | accuracy | **0.9481** |
| 3 | Chunk 检索 | 双路 | 70 行(自动生成) | reranked_recall@3 | **0.5869**(candidate_recall@20=0.9573) |
| 4 | Must-Point 覆盖 | 导师路 | 45 行(半自动) | point_f1 | **0.8299** |

## 3. 使用方法

### 3.1 一键跑全部评测

```powershell
# 一键跑全部评测
python -m eval.run_all --stages all
python -m eval.run_all --stages intent,gap,must_point  # 跳过检索(需 ChromaDB)
python -m eval.run_all --stages intent --verbose        # 单环节 + 错误详情

# 保存详细错误分析(v3/v5新增)
python -m eval.stages.eval_retrieval --verbose --save-verbose
python -m eval.stages.eval_must_point --verbose --save-verbose
```

输出:

```
Stage                     Metric          Value      Gold Size
------------------------------------------------------------
llm_intent_detection      llm_only_micro_f1 0.7576     50
gap_computation           accuracy        0.9481     104
chunk_retrieval           reranked_recall@3 0.5869     70
  - candidate_recall@20   recall          0.9573     70
  - reranked_recall@5    recall          0.7103     70
  - reranked_recall@8    recall          0.8059     70
  - final_context_hit@8  hit_rate        1.0000     70
  - tutor route           reranked_recall@3 0.7096   31
  - customer route        reranked_recall@3 0.4894   39
must_point_coverage       point_f1        0.8299     45
------------------------------------------------------------
End-to-end estimate: 0.3135
Bottleneck: chunk_retrieval (v7: recall@20 + rerank + context pack + MMR diversity)
```

**v7 架构说明**：
- 候选池：candidate_k=20/40（reply 保持轻量,finish/eval 使用更宽候选池）
- Rerank：轻量级多信号融合（语义/词汇/场景/类型/意图衰减）
- Context Pack：final_k=5/8 时启用 MMR 多样性选择，避免同质 chunk
- 目标：从 top3 升级到 top5/top8 上下文包，提升 LLM 决策质量

### 3.2 参数扫描

```powershell
# 单参数扫描
python -m eval.sweep --stage intent --param abs_floor --min 0.05 --max 0.3 --steps 11

# 多参数网格搜索(需用脚本传 JSON)
python -c "
from eval.sweep import _grid_sweep
results = _grid_sweep('intent', {'abs_floor': [0.05, 0.08, 0.10], 'rel_ratio': [0.5, 0.6, 0.75]})
for r in sorted(results, key=lambda x: -x['primary'])[:5]:
    print(r)
"
```

### 3.3 生成 Gold 数据

```powershell
python -m eval.gold_builder.build_retrieval_gold   # 自动,从 criteria 生成
python -m eval.gold_builder.build_gap_gold          # 半自动,需人工 review
python -m eval.gold_builder.build_must_point_gold   # 半自动,需人工 review
```

## 4. 各环节详解

### 4.1 意图检测评测(`eval/stages/eval_intent.py`)

**做什么**: 对每行 gold 数据,跑 `_build_customer_query_plan()` → `_select_intent_labels()`,对比预测标签与 gold_labels。

**Gold 数据**: `data/intent_eval_gold.jsonl`,193 行人工标注。每行:
```json
{"id": "IE_0001", "text": "...", "gold_labels": ["safety_concern", "rejection_or_hesitation"]}
```

**可调参数(v3优化后)**:
| 参数 | 含义 | 当前值 |
|------|------|--------|
| `abs_floor` | 绝对下限,分数低于此不选 | **0.08** |
| `rel_ratio` | 相对比例,必须 ≥ ratio × top_score | **0.50** |
| `intent_semantic_weight` | 意图语义权重 | **0.55** |
| `original_semantic_weight` | 原始query语义权重 | **0.25** |
| `keyword_recall_weight` | 关键词召回权重 | **0.10** |
| `keyword_overlap_weight` | 关键词重合权重 | **0.05** |

**per-label 诊断**:
| 标签 | P | R | F1 | 短板原因 |
|------|---|---|----|----|
| rate_concern | 0.70 | 0.76 | 0.73 | — |
| liquidity_concern | 0.88 | 0.58 | 0.70 | — |
| safety_concern | 0.45 | 0.60 | 0.51 | 关键词覆盖率一般 |
| procedure_question | 0.63 | 0.67 | 0.65 | — |
| rejection_or_hesitation | 0.65 | 0.24 | 0.35 | 表达多样,关键词难覆盖 |
| compliance_sensitive | 1.00 | 0.15 | 0.27 | 隐晦表达,关键词几乎无效 |

### 4.2 Gap 计算评测(`eval/stages/eval_gap.py`)

**做什么**: 对每行 gold 数据,跑 `analyze_customer_answer()` → `update_covered_intents()`,对比预测的 covered/missing 与 gold。

**Gold 数据**: `data/eval/gap_computation_gold.jsonl`,104 行半自动生成。三种覆盖类型:full(全覆盖)、partial(部分)、none(无覆盖)。

**关键指标**:
- `accuracy`: 每个 intent 的覆盖/未覆盖判断正确率
- `false_covered_rate`: 误判为已覆盖(最危险 — 导致系统跳过追问)
- `false_missing_rate`: 误判为未覆盖(影响较小 — 多追问一轮)

**可调参数**: `threshold`(当前 **0.10**,原 0.36)

### 4.3 Chunk 检索评测(`eval/stages/eval_retrieval.py`)

**做什么**: 对每行 gold 数据,跑 `retrieve_marketing_knowledge()`,对比返回的 chunk_ids 与 gold_chunk_ids。

**Gold 数据**: `data/eval/retrieval_gold.jsonl`,70 行自动生成(31 tutor + 39 customer)。

**两阶段检索架构**:

```
query
  ├─ Stage 1: Candidate Retrieval (候选召回)
  │  ├─ Vector semantic search (HyDE/original)
  │  ├─ Keyword lexical search
  │  └─ Intent-based search (customer route)
  │  └─ → 生成候选池 top20
  │
  ├─ Stage 2: Lightweight Rerank (轻量重排序)
  │  ├─ semantic_score: 融合分数 (40%)
  │  ├─ lexical_similarity: 文本相似度 (15%)
  │  ├─ scene_boost: 场景匹配 (20%)
  │  ├─ type_boost: 知识类型匹配 (10%)
  │  └─ rank_decay: 位置衰减 (15%)
  │  └─ → rerank_score 重排
  │
  └─ Stage 3: Final Selection (最终选择)
     └─ → 返回 top3/top5 给 LLM
```

**新增指标(v6两阶段架构)**:

| 指标 | 含义 | 用途 |
|------|------|------|
| candidate_recall@10 | 候选池 top10 中找到 gold 的比例 | 衡量第一阶段召回能力 |
| candidate_recall@20 | 候选池 top20 中找到 gold 的比例 | 衡量扩大候选池的效果 |
| reranked_recall@3 | rerank 后 top3 中找到 gold 的比例 | 衡量最终给 LLM 的上下文质量 |
| reranked_recall@5 | rerank 后 top5 中找到 gold 的比例 | 评估 top5 的召回能力 |
| precision@3/5 | topN 中真正属于 gold 的比例 | 评估检索精确度 |
| mrr | Mean Reciprocal Rank，gold 首次出现位置的倒数 | 评估 gold 排序质量 |
| ceiling@k | 数学上限 = min(k, len(gold)) / len(gold) | 计算理论最大 recall |
| normalized_candidate_recall@k | candidate_recall@k / ceiling@k | 候选阶段相对于理论上限的百分比 |
| normalized_reranked_recall@k | reranked_recall@k / ceiling@k | 重排后最终上下文相对于理论上限的百分比 |

**ceiling@k 原理**: 当 gold 数量 > k 时，recall@k 的数学上限必然 < 1.0。例如 gold 有 12 个 chunks，recall@3 最大只能达到 3/12 = 0.25。normalized_reranked_recall@k = 0.90 表示重排后的 top-k 达到了数学上限的 90%。

**可调参数(v7两阶段架构后)**:
| 参数 | 导师侧 | 客户侧 |
|------|--------|--------|
| Fusion Weights | hyde_semantic=0.50, original_semantic=0.25, keyword_overlap=0.10, type_boost=0.15 | intent_semantic=0.55, original_semantic=0.25, keyword_recall=0.10, keyword_overlap=0.05, intent_match=0.05 |
| **final_k** | reply=5 / finish=8 / eval=8 | reply=5 / eval=8 |
| **candidate_k** | 20-40 (内部候选池,可自适应调整) | 20-40 |
| Tutor Rerank Weights | semantic=0.35, lexical=0.15, scene=0.25, type=0.15, rank=0.10 | - |
| Customer Rerank Weights | - | semantic=0.45, lexical=0.15, scene=0.15, type=0.05, intent=0.10, rank=0.10 |
| eval_mode | False (生产) / True (评估) | False (生产) / True (评估) |

**参数语义说明(v7)**:
- `final_k`: 最终返回给LLM的chunk数量。reply 默认 5,finish 默认 8,避免模拟客户回复被过多上下文拖慢。
- `candidate_k`: 内部候选池大小,默认20,finish/eval 可提升到40。用于第一阶段召回,影响reranker输入质量,不会直接增加 LLM token。
- `AI_COACH_CHROMA_MAX_QUERY_RESULTS`: 底层 Chroma 单次查询上限,默认80,用于让 recall20/40 候选池真正生效。
- `eval_mode`: 评估模式下设为True,返回完整候选池和reranked结果用于分析。

**当前瓶颈分析(v7评估结果)**:
- **总体**:
  - candidate_recall@20: **0.9573** (候选池找到 95.7%)
  - reranked_recall@3: **0.5869** (最终 top3 召回达到数学上限)
  - final_context_hit@8: **1.0000** (给 LLM 的 top8 context pack 至少命中一个 gold chunk)
  - ceiling@3: 0.5869 (数学天花板)
  - normalized_reranked_recall@3: **1.0000** (达到天花板的 100%)

- **Tutor route**:
  - candidate_recall@20: **1.0000** (候选池找到 100%)
  - reranked_recall@3: **0.7096** (最终 top3 达到数学上限)
  - ceiling@3: 0.7096 (数学天花板)
  - normalized_reranked_recall@3: **1.0000** (达到天花板的 100%)
  - **Reranker 损失已清零** (top3 达到当前 gold 标注下的数学上限)

- **Customer route**:
  - candidate_recall@20: **0.9233** (候选池找到 92%)
  - reranked_recall@3: **0.4894** (最终 top3 召回 49%)
  - ceiling@3: 0.4894 (数学天花板)
  - normalized_reranked_recall@3: **1.0** (已达数学上限)
  - **主要瓶颈是天花板限制**，当 gold > 3 时 recall@3 上限 < 1.0

### 4.4 Must-Point 覆盖评测(`eval/stages/eval_must_point.py`)

**做什么**: 对每行 gold 数据,跑 `evaluate_coverage()`,对比预测覆盖的 must_points 与 gold。

**Gold 数据**: `data/eval/must_point_coverage_gold.jsonl`,45 行半自动生成。三种质量:good、partial、poor。

**可调参数(v5优化后)**:
| 参数 | 含义 | 当前值 |
|------|------|--------|
| `threshold` | 覆盖判定阈值 | **0.60** |
| `kw_weight` | 关键词权重 | **0.25** |
| `sem_weight` | 语义权重 | **0.75** |

**性能**: grid search显示当前最优组合为threshold=0.60, kw_weight=0.25, sem_weight=0.75，point_f1=0.7686，precision=0.7097，recall=0.8381。旧参数threshold=0.30, kw_weight=0.3, sem_weight=0.7会导致过度召回，precision下降明显。

## 5. 优化记录

### 首轮优化(2026-06-29)

| 环节 | 优化前 | 优化后 | 改动 |
|------|--------|--------|------|
| 意图检测 | F1=0.23 | **F1=0.55** (+138%) | `abs_floor` 0.20→0.08, `rel_ratio` 0.75→0.50 |
| Gap 计算 | acc=0.67 | **acc=0.95** (+42%) | `threshold` 0.36→0.10 |
| Must-Point | F1=0.71 | **F1=0.80** (+12%) | `threshold` 0.40→0.30 |
| **端到端** | **0.109** | **0.414** (+281%) | |

**瓶颈根因**: 所有阈值都定得过高。关键词+语义融合的分数分布通常在 0.05-0.30 之间,而阈值设在 0.20-0.40,导致大量真实信号被过滤。

### v3/v5优化(2026-07-03)

| 环节 | 优化前 | 优化后(v5预期) | 改动 |
|------|--------|---------------|------|
| 意图检测 | F1=0.55 | **F1=0.76** (+38%) | LLm-only策略,移除keyword干扰 |
| Chunk检索(tutor) | recall@3=0.50 | **recall@3=0.60** (+20%) | HyDE压缩、候选池扩大、权重调优 |
| Chunk检索(customer) | recall@3=0.35 | **recall@3=0.49** (+40%) | 意图语义权重提升、候选池扩大 |
| Must-Point | F1=0.73 | 旧预期 **F1=0.82** | 阈值0.30、权重(kw=0.3/sem=0.7),后续实测发现过度召回 |
| **端到端** | **0.414** | **0.282**(含检索) | 检索瓶颈缓解 |

**核心优化点**:
1. **HyDE查询压缩**: 移除模板冗余("员工回答或客户问题:"等),直接拼接核心语义
2. **融合权重调优**: 导师侧平衡语义与精确匹配,客户侧提升意图语义权重
3. **候选池扩大**: 导师top_k*10(上限50),客户top_k*12(上限60)
4. **场景优先强化**: 导师+0.12,客户+0.10,确保同场景优先
5. **权重组合优化**: kw_weight=0.3, sem_weight=0.7,提升语义判断权重

### v6两阶段架构优化(2026-07-03)

| 环节 | 优化前(v5) | 优化后(v6) | 改动 |
|------|-----------|-----------|------|
| Chunk检索(tutor) | recall@3=0.60 | **reranked_recall@3=0.67** (+12%) | 两阶段架构+轻量reranker |
| Chunk检索(customer) | recall@3=0.49 | **reranked_recall@3=0.49** (持平) | 两阶段架构+轻量reranker |
| Tutor normalized_reranked_recall@3 | - | **0.9462** | 达到天花板的94% |
| Customer normalized_reranked_recall@3 | - | **1.0** | 达到数学天花板 |

**核心优化点**:
1. **两阶段检索架构**: Stage1候选池(top20) → Stage2轻量rerank → Stage3最终选择
2. **ceiling@k指标**: 引入数学天花板概念,量化理论上限
3. **normalized_candidate/reranked_recall@k**: 区分候选召回和重排结果相对于天花板的百分比,更准确评估算法质量
4. **轻量reranker**: 多信号融合(semantic+lexical+scene+type+rank_decay)
5. **瓶颈诊断**: 区分candidate_miss(召回阶段)和rerank_miss(重排序阶段)

**当前评估结果(v6)**:
- Tutor route: candidate_recall@20=0.88 → reranked_recall@3=0.67, reranker损失约24%
- Customer route: candidate_recall@20=0.92 → reranked_recall@3=0.49,已达天花板

### v7参数语义重构与性能优化(2026-07-03)

| 环节 | 优化前(v6) | 优化后(v7) | 改动 |
|------|-----------|-----------|------|
| 参数语义 | top_k混淆 | **final_k/candidate_k分离** | 明确两阶段参数 |
| 评估模式 | 无法区分miss类型 | **eval_mode完整数据** | 支持候选池分析 |
| Route rerank权重 | 统一权重 | **TUTOR/CUSTOMER分离** | 路由特化优化 |
| 耗时统计 | 无 | **retrieval_elapsed_ms** | 性能监控 |

**核心优化点**:
1. **参数语义重构**:
   - `final_k` (默认3): 最终返回给LLM的chunk数量
   - `candidate_k` (默认20): 内部候选池大小
   - `eval_mode`: 评估时返回完整候选池和reranked结果

2. **Route-specific rerank权重**:
   - **TUTOR_RERANK_WEIGHTS**: semantic=0.35, lexical=0.15, scene=0.25, type=0.15, rank=0.10
   - **CUSTOMER_RERANK_WEIGHTS**: semantic=0.45, lexical=0.15, scene=0.15, type=0.05, intent=0.10, rank=0.10

3. **评估模式增强**:
   - `eval_mode=True` 时返回 `candidate_items` 和 `reranked_items`
   - 评估脚本正确区分 candidate_miss 和 rerank_miss
   - 支持 per-route 和 per-gold-count-group 分析

4. **性能保护**:
   - 添加 `retrieval_elapsed_ms` 耗时统计
   - 生产接口默认只返回 final items,不返回20条候选
   - 候选池计算不影响最终返回大小

**当前评估结果(v7)**:
- **总体**: candidate_recall@20=0.9573, reranked_recall@3=0.5869, normalized_reranked_recall@3=1.0000, final_context_hit@8=1.0000
- **Tutor**: candidate_recall@20=1.0000, reranked_recall@3=0.7096, normalized_reranked_recall@3=1.0000
- **Customer**: candidate_recall@20=0.9233, reranked_recall@3=0.4894, normalized_reranked_recall@3=1.0
- **瓶颈分析**:
  - Tutor route: 已达到当前 gold 标注下的 top3 理论天花板
  - Customer route: 已达数学天花板,recall@3=0.4894即为理论上限

### v8评估口径修正与Must-Point校准(2026-07-03)

| 环节 | 修正前 | 修正后 | 改动 |
|------|--------|--------|------|
| API兼容 | 部分调用仍传 `top_k` | `top_k` 作为 `final_k` 兼容别名 | 保持旧调用不崩溃 |
| 检索评估 | `precision@5` 受 `final_k=3` 影响 | 基于 `reranked_items` 计算 precision@3/5 | 指标口径更真实 |
| 归一化指标 | `normalized_recall@k` 含义混用 | 拆为 candidate/reranked 两类 | 区分候选召回与重排效果 |
| Must-Point | threshold=0.30, kw=0.3, sem=0.7 | threshold=0.60, kw=0.25, sem=0.75 | 降低误判覆盖 |

**当前主报告**:
- llm_intent_detection: llm_only_micro_f1=0.7576
- gap_computation: accuracy=0.9481
- chunk_retrieval: reranked_recall@3=0.5869, candidate_recall@20=0.9573, final_context_hit@8=1.0000
- must_point_coverage: point_f1=0.8299, precision=0.7353, recall=0.9524
- end_to_end_estimate=0.2449, bottleneck=chunk_retrieval（raw recall@3 受理论天花板限制）

## 6. 文件结构

```
eval/
    __init__.py
    run_all.py              # 主入口: python -m eval.run_all --stages all
    sweep.py                # 参数扫描: python -m eval.sweep --stage intent
    report.py               # JSON + ASCII 表格报告
    metrics.py              # 共享指标(StageResult, recall@k, mrr, point_prf1)
    stages/
        eval_intent.py      # 环节1: 意图检测
        eval_gap.py         # 环节2: Gap 计算
        eval_retrieval.py   # 环节3: Chunk 检索(v3: 增加失败模式分析)
        eval_must_point.py  # 环节4: Must-Point 覆盖(v5: 增加质量分级统计)
    gold_builder/
        build_retrieval_gold.py    # 自动: 从 criteria.source_chunk_ids 生成
        build_gap_gold.py          # 半自动: 模板 + 人工校验
        build_must_point_gold.py   # 半自动: 模板 + 人工校验
data/eval/
    report.json                    # 最新评测报告
    retrieval_gold.jsonl           # 70 行
    gap_computation_gold.jsonl     # 104 行
    must_point_coverage_gold.jsonl # 45 行
    retrieval_verbose_*.json       # v3/v5新增: 详细错误分析
    must_point_verbose_*.json      # v3/v5新增: 详细错误分析
```

## 7. 生产代码改动

为支持评测扫描,以下函数新增了可选参数(默认值不变,不影响现有行为):

| 函数 | 新增参数(v5/v3) |
|------|---------|
| `_build_tutor_hyde_query` | 查询压缩逻辑,移除模板冗余 |
| `_retrieve_tutor_hyde` | 候选池扩大(top_k*10,上限50),场景优先+0.12,权重调优 |
| `_retrieve_customer_intent_fusion` | 候选池扩大(top_k*12,上限60),场景优先+0.10,权重调优 |
| `retrieve_marketing_knowledge` | `fusion_weights: dict`(透传),版本标识 |
| `evaluate_coverage` | `kw_weight`, `sem_weight`(v5优化: 0.3/0.7) |
| `eval_retrieval.py` | `--save-verbose`,失败模式分析,按gold_count分组 |
| `eval_must_point.py` | `--save-verbose`,质量分级统计 |

### v6两阶段架构新增函数

| 函数 | 位置 | 功能 |
|------|------|------|
| `_lightweight_rerank()` | `app/core/marketing_rag.py` | 多信号轻量重排序 |
| `ceiling_at_k()` | `eval/metrics.py` | 计算数学天花板 |
| `normalized_recall_at_k()` | `eval/metrics.py` | 归一化召回率 |
| `DEFAULT_CANDIDATE_POOL_SIZE` | `app/core/marketing_rag.py` | 默认候选池大小(20) |
| `DEFAULT_FINAL_TOP_K` | `app/core/marketing_rag.py` | 默认最终返回数量(3) |
| `RERANK_WEIGHTS` | `app/core/marketing_rag.py` | Rerank特征权重配置 |

## 8. 待办

| 问题 | 路径 | 优先级 | 状态 |
|------|------|--------|------|
| ~~检索评测需 ChromaDB 已构建~~ | 先跑 `embedding_builder.py` 构建向量库 | 高 | ✅ 已完成 |
| ~~Gap/Must-Point gold 是半自动生成~~ | `needs_review=True`,人工校验后更准 | 中 | ✅ 已完成 |
| Gold标注过于宽泛导致理论天花板受限 | 重新标注,压缩gold数量 | 中 | 待定 |
| Tutor route reranker仍有损失 | 优化rerank权重或引入轻量Cross-Encoder实验 | 高 | 持续观察；当前normalized_reranked_recall@3=0.9462 |
| Customer route已达天花板,recall@3=0.49 | 扩大top_k或优化gold标注质量 | 低 | 持续观察 |
| 端到端瓶颈仍是chunk_retrieval | 持续优化两阶段架构 | 高 | 持续优化 |
| 持续监控生产数据表现 | 建立在线A/B测试机制 | 中 | 待定 |
| 异步化检索调用避免阻塞 | 在dialog_manager中使用asyncio.to_thread | 中 | 待定 |

## 9. 可选优化方向

### 方向1: 引入 Cross-Encoder 重度 reranker (低优先级)

**当前状态**: v7轻量reranker已达到较好效果
- Tutor: normalized_reranked_recall@3=0.9462 (天花板的94.6%)
- Customer: normalized_reranked_recall@3=1.0 (已达天花板)

**Cross-Encoder权衡**:
- ✅ 可能进一步提升排序质量,特别是边界case
- ❌ 需要额外模型依赖(如bge-reranker-base)
- ❌ 增加推理延迟(~50ms per query)
- ❌ 当前轻量reranker已达天花板94%+,收益有限

**建议**: 仅在以下情况考虑引入:
1. 生产数据发现大量rerank_miss导致业务问题
2. 端到端评估显示检索成为主要瓶颈
3. 愿意承担额外的模型依赖和延迟成本

### 方向2: 优化候选召回 (中优先级)

**当前状态**: candidate_recall@20=0.9573 (总体),top3 已达到当前 gold 标注下的理论天花板
- Tutor: candidate_recall@20=1.0000 (100%)
- Customer: candidate_recall@20=0.9233 (92.3%)

**优化策略**:
1. **增大候选池**: 从20增至30-40(尤其tutor route)
2. **调整fusion weights**: 当前tutor的hyde_semantic=0.50可能过高,可尝试降低
3. **添加更多召回源**: 如BM25、混合检索
4. **场景特化**: 高gold场景使用更大候选池

**预期收益**: 当前已达到 candidate_recall@20=0.95+；后续更适合优化 gold 标注粒度、E2E 评分稳定性和真实业务 case 覆盖。

### 方向3: 动态调整候选池大小 (中优先级)

**当前状态**: 已实现基础自适应(_get_adaptive_candidate_k)

**优化策略**:
1. **基于gold数量**: 在评估数据上统计每个场景的平均gold数量,动态调整候选池
2. **基于查询复杂度**: 长查询、多意图查询使用更大候选池
3. **基于场景ID**: 为特定场景设置预设倍数

**实现方式**:
```python
# 在 _get_adaptive_candidate_k 中添加
scene_gold_stats = {
    "INS_PERIODIC": {"avg_gold": 8, "multiplier": 2.0},
    "FUND_GENERAL": {"avg_gold": 12, "multiplier": 2.5},
    # ...
}
```

### 方向4: Learning-to-Rank 权重优化 (低优先级)

**当前状态**: 权重基于业务经验设定

**优化策略**:
1. 使用历史对话数据训练排序模型
2. 通过强化学习优化多阶段权重组合
3. A/B测试验证权重调整效果

**权衡**: 需要大量标注数据和计算资源,收益不确定

### 方向5: 异步化检索调用 (高优先级)

**当前状态**: 同步调用Chroma可能阻塞事件循环

**优化策略**:
在 `dialog_manager.py` 中使用 `asyncio.to_thread` 包装同步检索:
```python
retrieval_result = await asyncio.to_thread(
    retrieve_marketing_knowledge,
    query=query,
    route=route,
    final_k=final_k,
    scene_id=scene_id,
    # ...
)
```

**预期收益**:
- 避免并发请求互相卡住
- 提升整体吞吐量
- 不影响单次延迟

### 方向6: Gold标注质量优化 (中优先级)

**当前问题**: 部分查询的gold数量过多(>10),导致ceiling@3很低

**优化策略**:
1. 人工review当前gold标注,压缩冗余chunk
2. 制定gold标注规范: 每个查询最多5-8个gold chunk
3. 区分"必选"和"可选"gold,分层评估

**预期收益**: 提高ceiling@3,使recall@3指标更具意义
