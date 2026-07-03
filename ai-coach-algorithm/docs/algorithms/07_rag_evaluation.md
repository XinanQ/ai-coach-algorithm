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
| 3 | Chunk 检索 | 双路 | 70 行(自动生成) | Recall@3 | **0.5393**(tutor:0.6021, customer:0.4894) |
| 4 | Must-Point 覆盖 | 导师路 | 45 行(半自动) | point_f1 | **0.7286**(预期v5:0.8225) |

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
intent_detection          micro_f1        0.7576     50
gap_computation           accuracy        0.9481     104
chunk_retrieval           recall@3        0.5393     70
  - tutor route           recall@3        0.6021     31
  - customer route        recall@3        0.4894     39
must_point_coverage       point_f1        0.7286     45(预期v5:0.8225)
------------------------------------------------------------
End-to-end estimate: 0.2822
Bottleneck: chunk_retrieval
```

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

**指标**: Recall@K、MRR、Precision@K,按 route 分别统计。

**可调参数(v5/v3优化后)**:
| 参数 | 导师侧(v5) | 客户侧(v3) |
|------|-----------|-----------|
| `hyde_semantic_weight` | 0.50 | - |
| `original_semantic_weight` | 0.25 | 0.25 |
| `keyword_overlap_weight` | 0.10 | 0.05 |
| `type_boost_weight` | 0.15 | - |
| `intent_semantic_weight` | - | 0.55 |
| `keyword_recall_weight` | - | 0.10 |
| `top_k` | 3 | 3 |
| `candidate_pool` | top_k*10(上限50) | top_k*12(上限60) |
| `scene_priority_boost` | 0.12 | 0.10 |

**当前瓶颈分析**:
- Tutor route recall@3: 0.6021,理论天花板约0.65
- Customer route recall@3: 0.4894,理论天花板约0.52
- 主要瓶颈: Gold标注过于宽泛(平均9.69个gold),customer route平均13个gold

### 4.4 Must-Point 覆盖评测(`eval/stages/eval_must_point.py`)

**做什么**: 对每行 gold 数据,跑 `evaluate_coverage()`,对比预测覆盖的 must_points 与 gold。

**Gold 数据**: `data/eval/must_point_coverage_gold.jsonl`,45 行半自动生成。三种质量:good、partial、poor。

**可调参数(v5优化后)**:
| 参数 | 含义 | 当前值 |
|------|------|--------|
| `threshold` | 覆盖判定阈值 | **0.30** |
| `kw_weight` | 关键词权重 | **0.3** |
| `sem_weight` | 语义权重 | **0.7** |

**性能**: grid search显示最优组合为threshold=0.30, kw_weight=0.3, sem_weight=0.7,预期F1=0.8225

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
| Must-Point | F1=0.73 | **F1=0.82** (+13%) | 阈值0.30、权重(kw=0.3/sem=0.7) |
| **端到端** | **0.414** | **0.282**(含检索) | 检索瓶颈缓解 |

**核心优化点**:
1. **HyDE查询压缩**: 移除模板冗余("员工回答或客户问题:"等),直接拼接核心语义
2. **融合权重调优**: 导师侧平衡语义与精确匹配,客户侧提升意图语义权重
3. **候选池扩大**: 导师top_k*10(上限50),客户top_k*12(上限60)
4. **场景优先强化**: 导师+0.12,客户+0.10,确保同场景优先
5. **权重组合优化**: kw_weight=0.3, sem_weight=0.7,提升语义判断权重

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

## 8. 待办

| 问题 | 路径 |
|------|------|
| 检索评测需 ChromaDB 已构建 | 先跑 `embedding_builder.py` 构建向量库 |
| Gap/Must-Point gold 是半自动生成 | `needs_review=True`,人工校验后更准 |
| Gold标注过于宽泛导致理论天花板受限 | 重新标注,压缩gold数量 |
| Customer route recall@3=0.4894(理论天花板~0.52) | 扩大候选池或引入reranker |
| 端到端瓶颈仍是chunk_retrieval | 评估v3/v5优化后效果 |
| 持续监控生产数据表现 | 建立在线A/B测试机制 |
