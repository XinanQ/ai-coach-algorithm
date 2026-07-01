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
| 1 | 意图检测 | 客户路 | 193 行(人工标注) | micro_f1 | **0.5494** |
| 2 | Gap 计算 | 客户路 | 104 行(半自动) | accuracy | **0.9481** |
| 3 | Chunk 检索 | 双路 | 70 行(自动生成) | Recall@3 | 待跑(需 ChromaDB) |
| 4 | Must-Point 覆盖 | 导师路 | 45 行(半自动) | point_f1 | **0.7951** |

## 3. 使用方法

### 3.1 一键跑全部评测

```powershell
python -m eval.run_all --stages all
python -m eval.run_all --stages intent,gap,must_point  # 跳过检索(需 ChromaDB)
python -m eval.run_all --stages intent --verbose        # 单环节 + 错误详情
```

输出:

```
Stage                     Metric          Value      Gold Size
------------------------------------------------------------
intent_detection          micro_f1        0.5494     193
gap_computation           accuracy        0.9481     104
must_point_coverage       point_f1        0.7951     45
------------------------------------------------------------
End-to-end estimate: 0.4142
Bottleneck: intent_detection
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

**可调参数**:
| 参数 | 含义 | 当前值 | 优化前 |
|------|------|--------|--------|
| `abs_floor` | 绝对下限,分数低于此不选 | **0.08** | 0.20 |
| `rel_ratio` | 相对比例,必须 ≥ ratio × top_score | **0.50** | 0.75 |
| `kw_weight` | 关键词融合权重 | 0.55 | 0.55 |
| `sem_weight` | 语义融合权重 | 0.45 | 0.45 |

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

**可调参数**: fusion_weights(客户路 5 个权重,导师路 3 个权重),top_k。

### 4.4 Must-Point 覆盖评测(`eval/stages/eval_must_point.py`)

**做什么**: 对每行 gold 数据,跑 `evaluate_coverage()`,对比预测覆盖的 must_points 与 gold。

**Gold 数据**: `data/eval/must_point_coverage_gold.jsonl`,45 行半自动生成。三种质量:good、partial、poor。

**可调参数**:
| 参数 | 含义 | 当前值 | 优化前 |
|------|------|--------|--------|
| `threshold` | 覆盖判定阈值 | **0.30** | 0.40 |
| `kw_weight` | 关键词权重 | 0.4 | 0.4 |
| `sem_weight` | 语义权重 | 0.6 | 0.6 |

## 5. 优化记录

### 首轮优化(2026-06-29)

| 环节 | 优化前 | 优化后 | 改动 |
|------|--------|--------|------|
| 意图检测 | F1=0.23 | **F1=0.55** (+138%) | `abs_floor` 0.20→0.08, `rel_ratio` 0.75→0.50 |
| Gap 计算 | acc=0.67 | **acc=0.95** (+42%) | `threshold` 0.36→0.10 |
| Must-Point | F1=0.71 | **F1=0.80** (+12%) | `threshold` 0.40→0.30 |
| **端到端** | **0.109** | **0.414** (+281%) | |

**瓶颈根因**: 所有阈值都定得过高。关键词+语义融合的分数分布通常在 0.05-0.30 之间,而阈值设在 0.20-0.40,导致大量真实信号被过滤。

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
        eval_retrieval.py   # 环节3: Chunk 检索
        eval_must_point.py  # 环节4: Must-Point 覆盖
    gold_builder/
        build_retrieval_gold.py    # 自动: 从 criteria.source_chunk_ids 生成
        build_gap_gold.py          # 半自动: 模板 + 人工校验
        build_must_point_gold.py   # 半自动: 模板 + 人工校验
data/eval/
    report.json                    # 最新评测报告
    retrieval_gold.jsonl           # 70 行
    gap_computation_gold.jsonl     # 104 行
    must_point_coverage_gold.jsonl # 45 行
```

## 7. 生产代码改动

为支持评测扫描,以下函数新增了可选参数(默认值不变,不影响现有行为):

| 函数 | 新增参数 |
|------|---------|
| `_build_customer_query_plan` | `kw_weight`, `sem_weight` |
| `_retrieve_customer_intent_fusion` | `fusion_weights: dict` |
| `_retrieve_tutor_hyde` | `fusion_weights: dict` |
| `retrieve_marketing_knowledge` | `fusion_weights: dict`(透传) |

## 8. 待办

| 问题 | 路径 |
|------|------|
| 检索评测需 ChromaDB 已构建 | 先跑 `embedding_builder.py` 构建向量库 |
| Gap/Must-Point gold 是半自动生成 | `needs_review=True`,人工校验后更准 |
| `rejection_or_hesitation` recall 仅 24% | 扩充关键词表 or 启用 BERT-mini |
| `compliance_sensitive` recall 仅 15% | 需模型层面提升(关键词天然弱项) |
| 端到端估算不含检索环节 | ChromaDB 构建后补充 |
