# 算法文档 04 — 意图理解

> 涉及代码:
> - 推理:[customer_answer_understanding.py](../../app/core/customer_answer_understanding.py) + [intent_labels.py](../../app/core/intent_labels.py)
> - 训练框架:[intent_eval_set_builder.py](../../app/core/intent_eval_set_builder.py) + [intent_dataset_prep.py](../../app/core/intent_dataset_prep.py) + [intent_threshold_calibrator.py](../../app/core/intent_threshold_calibrator.py) + [bert_mini_trainer.py](../../app/core/bert_mini_trainer.py) + [intent_model_eval.py](../../app/core/intent_model_eval.py)
> - 模型 adapter:[bert_mini_intent_classifier.py](../../app/core/bert_mini_intent_classifier.py)

## 1. 核心问题

陪练系统需要识别"员工答了客户哪些顾虑"。这是一个**中文多标签短文本分类**问题,要求:

| 要求 | 含义 |
|---|---|
| **多标签** | 一句话可以同时是 rate_concern + safety_concern |
| **多类型** | 客户问句和员工答句都要处理(同一套标签) |
| **轻量** | 评分链路里跑,延迟不能高 |
| **可控** | 阈值可标定,而不是 LLM 黑盒 |

## 2. 6 个意图标签

定义在 [intent_labels.py](../../app/core/intent_labels.py):

| label | 中文 | 含义 | 关键词样例 |
|---|---|---|---|
| `rate_concern` | 利率收益 | 利率/收益/同业比较 | 利率、收益、高一点、划算、利息 |
| `liquidity_concern` | 流动性 | 提前支取/期限灵活 | 急用、随时、提前取、短期、活期 |
| `safety_concern` | 安全 | 本金/风险/亏损 | 风险、亏、本金、安全吗、保本 |
| `procedure_question` | 办理流程 | 流程/材料/查询 | 怎么办、办理、流程、材料、网点 |
| `rejection_or_hesitation` | 拒绝犹豫 | 再考虑/不要 | 再看看、考虑、不用、犹豫、商量 |
| `compliance_sensitive` | 合规敏感 | 承诺/保证/最高收益 | 保证、最高、稳赚、承诺、绝对 |

**标签选择原则**(为什么是这 6 个):
- 跟金融营销实际客户顾虑对齐(覆盖 ~95% 真实异议场景)
- 跟 rubric 评分维度互通(`compliance_sensitive` ↔ 合规度,`rejection_or_hesitation` ↔ 共情力)
- 数量克制(6 个,标注成本可控,标签互斥度高)

## 3. 推理路径(当前)

### 3.1 统一入口

**全仓库唯一**的意图识别入口:`analyze_customer_answer(text)`。`dialog_manager` / `marketing_rag` / `rule_scorer` 三处消费方都走这一个函数。

设计原则:**单一真相源**。各处算意图不会有口径差异。

### 3.2 当前实现:纯关键词

```python
def keyword_intent_scores(text: str) -> dict[str, float]:
    # 每个标签:命中关键词数 / 关键词总数
    scores = {}
    for label, keywords in INTENT_KEYWORDS.items():
        hit = sum(1 for kw in keywords if kw in text)
        scores[label] = round(hit / max(len(keywords), 1), 4)
    return scores

def analyze_customer_answer(text: str) -> dict:
    keyword_scores = keyword_intent_scores(text)
    # 当前 BERT 禁用,直接返回 keyword 分数
    # 若 BERT 启用且融合开关打开:0.70 × bert + 0.30 × keyword
    ...
    return {
        "text": cleaned,
        "intent_labels": [...],          # > 0 的标签
        "intent_scores": fused,           # 每个标签的 0-1 分数
        "keyword_intent_scores": keyword_scores,
        "bert_mini_available": bool,
        "bert_mini_scores": bert_scores,  # 全 0,因为禁用
        "risk_flags": [compliance_sensitive 时单独标记],
        "method": "keyword_baseline_bert_mini_disabled",
    }
```

### 3.3 BERT-mini 现状(禁用中)

`AI_COACH_BERT_MINI_FUSION` 环境变量默认 `0`,即禁用 BERT-mini 融合。

**原因**(已实测):
- 当前训练 epoch 5 之后 F1=0(模型崩盘)
- Trainer 保存的是最后一轮的崩盘模型
- 启用 BERT 融合会把 keyword 的 F1=0.58 拖到 0(因为 `0.70 × 0 + 0.30 × 0.58 = 0.17`)

**未来启用方式**:
1. 修 `bert_mini_trainer.py` 保存最佳 epoch 而不是最后 epoch
2. 补样本到 300+(每标签 ≥ 30,procedure_question 和 compliance_sensitive 当前稀缺)
3. 降学习率(5e-6 而不是 2e-5)
4. 重训后 `set AI_COACH_BERT_MINI_FUSION=1`,代码自动启用融合

**为什么暂不优先修**:LLM 客户已经接管追问生成,gap 检测的语义压力下降。BERT 优先级降级。

## 4. 阈值标定

### 4.1 关键阈值:`update_covered_intents` 的判定阈值

```python
def update_covered_intents(previous_covered, intent_scores, threshold=0.36):
    covered = set(previous_covered)
    for intent, score in intent_scores.items():
        if score >= threshold:
            covered.add(intent)
    return sorted(covered)
```

`threshold=0.36` 是**经 193 条 gold 数据集标定**得来。之前是经验值 0.05(太松,几乎所有员工话都被标"已覆盖")。

### 4.2 标定流程(`intent_threshold_calibrator.py`)

```python
# 输入:gold 标注集(193 条人工标 gold_labels)
# 算法:从 0.05 到 0.95 网格搜索,每个阈值算 micro F1
# 输出:micro_f1 最大的阈值 = 0.36
```

跑法:

```powershell
.\.venv\Scripts\python.exe -m app.core.intent_threshold_calibrator
```

输出会打印每个阈值对应的 micro_f1 / precision / recall。**需要手动把最优值回填到 `coverage.update_covered_intents` 的默认参数**(已回填 0.36)。

## 5. 标注框架(完整工作流)

```
intent_eval_set_builder    →  178 条候选
       ↓ 人工标 gold(intent_eval_gold.jsonl)
intent_dataset_prep        →  train/eval 切分(70/30)
       ↓
intent_threshold_calibrator → 标定 keyword 阈值
intent_model_eval           → 评测 baseline / BERT-mini
bert_mini_trainer          →  可选:训练 BERT-mini(当前不优先)
```

详细规范:[../intent_annotation_schema.md](../intent_annotation_schema.md)

### 5.1 候选生成(`intent_eval_set_builder.py`)

策略:
- 从 `customer_profiles.json` 抽 opening / concern
- 从 `marketing_chunks.json` 抽 customer_query / customer_view_text
- 从 longterm_memory 抽真实对话(若有)
- 去重 + 按标签做轻度分层(避免某个标签 0 样本)
- 关键词预标(`suggested_labels`)作为标注辅助

### 5.2 标注规范要点(详见 schema 文档)

| 原则 | 说明 |
|---|---|
| **看语义不看关键词** | "怎么办"≠ procedure_question(可能是表达无奈) |
| **允许多标签** | 同时是 rate + safety 完全 OK |
| **无关句留 `[]`** | 是有价值的负样本 |
| **`compliance_sensitive` 看表述不看角色** | 客户说"你能保证吗"也算 |
| **频道无关** | 同一句话不同 scene 标签一致 |

### 5.3 当前 gold 集状态

- **总量**:193 条已标
- **稀缺标签**:`procedure_question`(8 条)、`compliance_sensitive`(5 条)需要补
- **负样本**:`[]` 的真负样本约 30 条
- **未充分标注**:员工答句多于客户问句,需要补员工话样本

## 6. 调优入口速查

| 想改什么 | 改哪里 |
|---|---|
| 加 / 删意图标签 | `intent_labels.INTENT_LABELS` + 同步改 `INTENT_KEYWORDS` 和 `INTENT_LABEL_DESCRIPTIONS` |
| 改某标签的关键词 | `intent_labels.INTENT_KEYWORDS[label]` |
| 改覆盖判定阈值 | `coverage.update_covered_intents(threshold=0.36)` |
| 改意图标签选择阈值(检索用) | `marketing_rag.INTENT_ABS_FLOOR / INTENT_REL_RATIO` |
| 改 BERT/keyword 融合权重 | `customer_answer_understanding.analyze_customer_answer` 第 27 行 `0.70/0.30` |
| 启用 BERT-mini 融合 | `$env:AI_COACH_BERT_MINI_FUSION=1` |
| 改 BERT 训练超参 | `bert_mini_trainer.py` |
| 标注 schema 改了 | `intent_eval_set_builder._suggested_labels` |
| 重新标定阈值 | 跑 `intent_threshold_calibrator`,改 gold 后必跑 |

## 7. 已知限制与待办

| 问题 | 现状 | 路径 |
|---|---|---|
| BERT-mini 训练崩盘(F1=0) | 已禁用,纯 keyword 跑 | 修 trainer + 补样本 + 重训 |
| 关键词模型语义判别弱 | 已知 | LLM 客户已经接管追问,问题被绕开 |
| `procedure_question` / `compliance_sensitive` 样本稀缺 | < 10 条 | 补到每标签 ≥ 30 条 |
| 员工答句标注少 | 已知 | 标注时多覆盖员工话 |
| 阈值标定只用 micro_f1 | 已知 | 可加 per-label 阈值,但目前粒度够 |
| 无 BERT 训练回归测试 | 已知 | 训练完手动跑 intent_model_eval 对比 |

## 8. 失败回退

| 失败点 | 兜底 | 影响 |
|---|---|---|
| BERT 模型不可用 | 走 keyword,`bert_mini_available=False` | 已经是当前默认状态,无影响 |
| 文本为空 | 全部标签 score = 0,intent_labels = [] | 安全 |
| 关键词词表加载失败 | 抛 ImportError | 启动失败,需立刻修 |

## 9. 演示亮点

意图识别本身不是用户可见的功能,但是它的**输出驱动了 LLM 客户的 gap 信号**。演示时可以:

1. 打开 `/rag/marketing/customer-answer-understanding` 接口,输入员工话,看返回的 `intent_scores` 和 `intent_labels`
2. 演示同一句话在不同表达下的 keyword 命中差异(展示当前关键词的限制)
3. 展示 `data/intent_eval_gold.jsonl` 的标注样本,说明系统不是黑盒——是用人工标注数据校准过的

## 10. 长期演进

| 阶段 | 内容 |
|---|---|
| 当前 | 关键词 + 阈值标定 |
| 短期 | BERT-mini 重训正常后启用融合 |
| 中期 | 用 LLM 做意图识别(每轮 +1 次 LLM 调用,语义最强但贵) |
| 长期 | 训自家小模型(Qwen2.5-1.5B 之类),性能 + 成本 + 隐私三者兼顾 |
