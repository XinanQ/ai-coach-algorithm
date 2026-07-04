# E2E (End-to-End) 评测体系

## 概述

端到端（E2E）评测模拟完整的陪练对话流程，验证从 `start_dialogue` → 多轮 `reply_dialogue` → `finish_dialogue` 的整个链路。

## 评测架构

### E2E Case 数据结构

每条 E2E 测试用例包含：

```json
{
  "id": "e2e_001",
  "user_id": "eval_user_001",
  "scene_id": "INS_PERIODIC",
  "customer_id": null,
  "task_id": null,
  "total_rounds": 3,
  "employee_messages": [
    "第一轮员工回答...",
    "第二轮员工回答...",
    "第三轮员工回答..."
  ],
  "expected_intents": ["compliance_sensitive", "rate_concern", "procedure_question"],
  "expected_gap_after_each_turn": [[], [], []],
  "expected_followup_direction": [
    "追问保本承诺的合规性",
    "追问收益率具体数字和比较",
    "确认办理流程和所需材料"
  ],
  "expected_must_points": ["避免承诺收益", "风险揭示", "合规边界"],
  "expected_weak_tags": ["合规揭示不足", "风险说明缺失"],
  "expected_score_range": [40, 60],
  "forbidden_outputs": ["reply中不应出现liveScore或source字段"]
}
```

### 评测指标

E2E 评测分为多个可解释的子指标：

| 指标 | 说明 | 期望值 |
|------|------|--------|
| `contract_pass` | 接口契约符合性：reply 不返回 liveScore/source | 100% |
| `intent_pass` | 每轮意图识别合理性 | > 80% |
| `gap_pass` | 漏答项计算准确性 | > 90% |
| `retrieval_hit` | RAG 上下文包含关键知识 | > 70% |
| `followup_pass` | AI 客户追问方向符合预期 | > 75% |
| `finish_score_pass` | 最终分数落在合理区间 | > 80% |
| `weak_tag_pass` | 弱点标签命中相关性 | > 70% |
| `e2e_overall_pass` | 综合通过（所有子指标通过） | 目标 > 60% |

## 运行 E2E 评测

### 完整评测

```bash
# 运行所有评测阶段（包括 E2E）
python -m eval.run_all --stages all

# 仅运行 E2E 评测
python -m eval.stages.eval_e2e --sample-size 10 --verbose

# 跳过 LLM 依赖的验证（快速反馈）
python -m eval.stages.eval_e2e --skip-slow --sample-size 5
```

### 保存详细 trace

```bash
python -m eval.stages.eval_e2e --verbose --save-trace
```

输出文件：`data/eval/e2e_verbose_TIMESTAMP.json`

## E2E 数据集

### 当前覆盖

- 8 条测试用例，覆盖：
  - 合规敏感场景（错误承诺）
  - 正常回答场景
  - 不同产品类型（保险、基金、理财）
  - 不同客户顾虑类型

### 扩展指南

添加新用例至 `data/eval/e2e_dialog_gold.jsonl`：

```jsonl
{"id": "e2e_XXX", "user_id": "eval_user_XXX", "scene_id": "SCENE_ID", ...}
```

关键字段：
- `employee_messages`: 必填，至少 1 轮
- `expected_intents`: 建议填写，用于意图验证
- `expected_score_range`: 建议填写，用于分数验证
- `forbidden_outputs`: 建议填写，用于契约验证

## 失败分析

### 失败分类

E2E 失败按阶段分类：

1. **contract_fail**: reply 返回了不应有的字段
2. **intent_fail**: 意图识别与预期不符
3. **gap_fail**: 漏答计算错误
4. **retrieval_fail**: RAG 未检索到相关知识
5. **followup_fail**: 追问方向偏离预期
6. **score_fail**: 最终评分超出合理区间
7. **weak_tag_fail**: 弱点标签不相关

### 典型问题

| 问题类型 | 表现 | 修复方向 |
|----------|------|----------|
| 契约违反 | reply 包含 liveScore | 检查 dialog_presenter.py |
| 意图漏检 | 未识别到 compliance_sensitive | 调整 LLM prompt 或 keyword 规则 |
| RAG 召回失败 | 关键知识未在 top3 | 增加 candidate_k 或优化 rerank |
| 追问重复 | 连续追问同一问题 | 检查 gap 跟踪逻辑 |

## 与单点指标的关系

| 单点指标 | E2E 对应 | 关联 |
|----------|----------|------|
| `llm_intent_detection` | `intent_pass` | 意图识别准确率 |
| `gap_computation` | `gap_pass` | 漏答计算准确性 |
| `chunk_retrieval` | `retrieval_hit` | RAG 质量影响追问和评分 |
| `must_point_coverage` | `finish_score_pass` | 必讲点覆盖影响最终评分 |

**注意**：E2E 通过率 ≠ 单点指标相乘。E2E 反映真实业务场景的综合正确率。

## 持续改进

### 优化路线

1. **扩展数据集**：从 8 条扩展到 50+ 条，覆盖更多场景
2. **细化指标**：增加追问质量、对话连贯性等维度
3. **自动化回归**：CI 集成 E2E 评测
4. **根因分析**：失败 case 自动归类并指向上游模块

### 监控指标

- `e2e_overall_pass` 趋势（目标：每周提升 5-10%）
- 各子指标分布（识别短板）
- 失败 case 累计（需人工 review）
