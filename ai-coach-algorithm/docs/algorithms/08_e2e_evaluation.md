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
| `retrieval_hit` | RAG 上下文包含关键知识（必须命中 expected_must_points 或相关关键词） | > 70% |
| `followup_pass` | AI 客户追问方向符合预期（必须匹配 gap intent 或 expected_followup_direction） | > 75% |
| `finish_score_pass` | 最终分数落在合理区间（校准后：合规红线 0-40，好回答 80-95） | > 80% |
| `weak_tag_pass` | 弱点标签命中相关性（expected_weak_tags 非空时必须检测到标签） | > 70% |
| `e2e_overall_pass` | 综合通过（所有子指标通过） | 目标 > 60% |

### 当前基线（2026-07-05）

当前完整评估通过 `python -m eval.run_all --stages all` 生成，E2E 阶段结果如下：

| 指标 | 当前值 |
|------|--------|
| `e2e_overall_pass` | 0.70 |
| `start_pass` | 1.00 |
| `contract_pass` | 1.00 |
| `intent_pass` | 1.00 |
| `gap_pass` | 1.00 |
| `retrieval_hit` | 0.95 |
| `followup_pass` | 1.00 |
| `finish_score_pass` | 0.80 |
| `weak_tag_pass` | 0.90 |

E2E evaluator 使用每次运行独立的临时 JSON memory，避免读写 `mock_db/mock_dialog_sessions.json` 等本地开发状态，降低历史 session 或并发运行造成的评估波动。`start_pass` 已纳入 overall 计算，确保 start 阶段失败不会被隐藏为后续 finish 失败。

### 评测规则更新（2026-07-04）

#### retrieval_hit 收紧规则
- **旧规则**：只要返回 items 就算通过
- **新规则**：
  - 如果 `expected_must_points` 非空，必须命中至少一个关键词
  - 提取 `expected_must_points` 中的中文关键词（2+ 字符）
  - 检查 top-5 检索结果的 content/title 是否包含关键词
  - 如果 `expected_must_points` 非空但无任何命中 → FAIL

#### followup_pass 收紧规则
- **旧规则**：文本长度 > 3 就放行
- **新规则**：
  - 必须匹配 gap intent 的关键词 或 expected_followup_direction 的关键词
  - 扩展 intent 关键词表（每个 intent 5-7 个关键词）
  - 如果没有任何关键词匹配 → FAIL
  - 禁止单纯靠长度放行

#### weak_tag_pass 收紧规则
- **旧规则**：未检测到标签也算通过
- **新规则**：
  - 如果 `expected_weak_tags` 非空，必须检测到至少一个相关标签
  - 支持 2-4 字符子串匹配
  - 如果 `expected_weak_tags` 非空但 `weak_tags` 为空 → FAIL

#### finish_score_pass 校准
- **旧规则**：gold 中的评分区间校准不足
- **新规则**：
  - 合规红线：0-40 分
  - 中等回答：50-75 分
  - 好回答：80-98 分
  - 重新校准所有 gold 的 `expected_score_range`

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

- **20 条测试用例**，扩展覆盖：
  - **合规红线场景**（5 条）：
    - 保本保息承诺
    - 绝对保本/稳赚
    - 收益写进合同
    - 明确表示没风险
  - **好回答场景**（6 条）：
    - 明确风险揭示
    - 不承诺收益
    - 有适当性管理
    - 共情理解客户
    - 根据风险承受能力推荐
  - **中等回答场景**（6 条）：
    - 讲了风险但不完整
    - 讲了流程但缺少引导
    - 信息过载缺乏重点
    - 多轮修正（第一轮踩红线后纠正）
  - **异议处理场景**（2 条）：
    - 灵活性异议（好回答）
    - 犹豫异议（强推销回答）
  - **电话邀约场景**（1 条）

### 评分区间校准

| 场景类型 | 预期分值区间 | 说明 |
|----------|--------------|------|
| 合规红线 | 0-40 | 承诺收益、保本保息、绝对保本等严重合规问题 |
| 信息不足 | 20-40 | 几乎没有提供有用信息 |
| 中等回答 | 40-65 | 有一些有用信息但缺关键要素（如办理流程） |
| 中等偏上 | 50-75 | 有一定合规揭示和适当性管理 |
| 好回答 | 75-95 | 全面的风险揭示、适当性管理、需求确认 |

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
