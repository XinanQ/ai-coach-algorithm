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
  "expected_customer_evidence": ["追问保本承诺的合规性", "追问收益率具体数字和比较"],
  "expected_customer_evidence_after_each_turn": [
    ["保本承诺", "合规边界"],
    ["收益比较"],
    ["办理流程", "所需材料"]
  ],
  "customer_evidence_status": "derived_v2",
  "expected_tutor_evidence": ["避免承诺收益", "风险揭示", "合规边界"],
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
| `customer_retrieval_hit` | reply 的客户侧 RAG 命中客户顾虑/追问素材 | > 90% |
| `tutor_retrieval_hit` | finish 的导师侧 RAG 命中 must points/评分依据 | > 95% |
| `followup_pass` | AI 客户追问方向符合预期（必须匹配 gap intent 或 expected_followup_direction） | > 75% |
| `dynamic_dialogue_pass` | start/reply 动态链路通过，不受 finish 分数带宽与弱点标签影响 | > 80% |
| `finish_score_pass` | 最终分数落在合理区间（校准后：合规红线 0-40，好回答 80-95） | > 80% |
| `strict_score_pass` | 最终分数落在更窄业务区间，只有配置 `strict_score_range` 的 case 会比标准口径更严格 | > 80% |
| `weak_tag_pass` | 弱点标签命中相关性（expected_weak_tags 非空时必须检测到标签） | > 70% |
| `e2e_overall_pass` | 动态 transcript 与 `legacy_unbound` 分数带宽的混合诊断值 | 诊断项 |
| `strict_e2e_overall_pass` | 严格综合通过，防止 gold 区间过宽导致指标虚高 | 目标 > 60% |

### 当前三个口径（2026-07-10）

| 口径 | 当前值 | 用途 |
|---|---:|---|
| rule E2E 回归 | 0.80 | 确定性守护链路，不代表生产 LLM 质量 |
| 动态 E2E 生产混合口径 | 0.36 | 动态客户 + 检索 + 旧 score band 的组合压力指标 |
| scorer_transcript | 0.94 | 50 条人工审定固定 transcript；平均带宽偏差 0.10，50/50 LLM |

上述 `0.80` 与 `0.36` 是 v1 历史基线，不能和采用双路检索证据、语义追问
校验及标准标签词表的 v2 指标直接做升降对比。v2 报告会写入
`evaluation_schema_version=2`、`metric_contract` 和 `runtime_config`；其中
`dynamic_dialogue_pass` 是 v2 的主指标，专门衡量动态 start/reply。`e2e_overall_pass`
继续展示包含导师检索、最终评分和弱点标签的混合结果，但动态客户问题每次变化，旧分数
带宽没有绑定当前 transcript，因此该值仅供定位压力，不可引用为系统端到端正确率。

客户侧检索按 `expected_customer_evidence_after_each_turn[turn_idx]` 逐轮验收，不能用
整场对话任意一个未来方向替当前轮次通过。旧数据仍兼容 `expected_customer_evidence`，
但新增或人工校准 case 应优先填写逐轮字段。`derived_v2` 表示业务锚点由已审定的
follow-up direction 确定性生成；人工确认后可改为 `reviewed`，迁移脚本不会覆盖。
“客户可能同意/决定”等纯行为结果不伪造 RAG 证据要求。
报告中的 `gold_annotation_coverage.followup_turn_coverage` 会显示已审定追问方向覆盖了
多少员工轮次；逐轮字段存在但某轮未标注时，该轮不继承整场旧字段，也不计为检索失败。

客户侧 rerank 对多个 gap intent 取“最强匹配”而不是平均匹配，避免一个 chunk 对某项
顾虑高度相关却被其他未命中意图稀释。final-5 context pack 固定保留前 4 个相关结果，
剩余 1 个位置再做多样性选择；该调整不增加候选数、LLM token 或额外模型调用。

`scorer_transcript` 的人工带宽只对其完整 `dialog_pairs` 生效。每条 reviewed case
都必须保存 `transcript_hash`；修改客户问题或员工回答后，旧带宽自动失效。不能仅按
case id 把固定 transcript 带宽覆盖到每次都会重新生成客户追问的动态 E2E。

正式 scorer 基线默认要求全部 case 使用 `llm_scorer_*`。出现任何 rule fallback
会直接失败；只有诊断时才能显式传 `--allow-rule-fallback`。

### v2 离线诊断基线（2026-07-10）

以下结果使用 `AI_COACH_CUSTOMER_LLM=template`、`AI_COACH_SCORER=rule` 和
`sentence_transformers`，用于确定性诊断，不是生产 LLM 指标，也不会覆盖正式 report：

| 指标 | 数值 |
|---|---:|
| `dynamic_dialogue_pass` | 0.62 |
| `e2e_overall_pass` | 0.46 |
| `customer_retrieval_hit` | 0.80 |
| `tutor_retrieval_hit` | 0.98 |
| `followup_pass` | 0.72 |
| `finish_score_pass` | 0.86 |
| `weak_tag_pass` | 0.94 |
| follow-up gold 轮次覆盖率 | 0.7872（74/94） |

独立 retrieval 回归为 `final_context_recall@8=0.8059`，其中 tutor 为 `0.9135`、
customer 为 `0.7204`，`context_hit@8=1.0`。客户 E2E 剩余失败的分层诊断显示：
候选召回缺失 4 轮、rerank top-5 丢失 7 轮、context-pack 丢失 1 轮，因此本轮只调整
客户 rerank 信号，不增加候选池、final context 或 LLM 调用成本。

Docker 启动后，正式验证必须分别运行：

```powershell
docker compose exec ai-coach-api python -m pytest tests/test_eval_quality_guards.py -q
docker compose exec ai-coach-api python -m eval.stages.eval_scorer --verbose
docker compose exec ai-coach-api python -m eval.stages.eval_e2e
```

第二条若任何 case 发生 rule fallback 会返回非零退出码；只有 50/50 都是
`llm_scorer_*` 才能引用为正式 scorer 基线。

### 历史基线（2026-07-06）

当前 E2E 基线通过 `python -m eval.stages.eval_e2e` 生成，E2E 阶段结果如下：

| 指标 | 当前值 |
|------|--------|
| `e2e_overall_pass` | 以当前 `data/eval/report.json` 为准 |
| `start_pass` | 1.00 |
| `contract_pass` | 1.00 |
| `intent_pass` | 1.00 |
| `gap_pass` | 1.00 |
| `retrieval_hit` | 1.00 |
| `followup_pass` | 1.00 |
| `finish_score_pass` | 以当前 `data/eval/report.json` 为准 |
| `strict_score_pass` | 以当前 `data/eval/report.json` 为准 |
| `strict_e2e_overall_pass` | 以当前 `data/eval/report.json` 为准 |
| `weak_tag_pass` | 以当前 `data/eval/report.json` 为准 |

E2E evaluator 使用每次运行独立的临时 JSON memory，避免读写 `mock_db/mock_dialog_sessions.json` 等本地开发状态，降低历史 session 或并发运行造成的评估波动。`start_pass` 已纳入 overall 计算，确保 start 阶段失败不会被隐藏为后续 finish 失败。

注意：`data/eval/report.json` 应在带 `sentence_transformers` / Docker 项目环境中通过 `python -m eval.run_all --stages all` 刷新，避免用轻量 fallback 环境覆盖正式 embedding 指标。

### Gold 校准原则（2026-07-06）

- `expected_score_range` 表示业务可接受区间，不能为了贴合当前 scorer 输出而任意放宽。
- `strict_score_range` 表示更窄的业务验收区间，用来识别“标准口径通过但评分仍偏松/偏低”的 case。
- 修改 gold 时需要写入 `calibration_reason`，说明该区间来自业务判断，而不是为了追求 E2E 100%。
- 合同阅读、风险提示、资料提供等动作不自动等同于成交引导；如果缺少下一步动作，仍应保留相应弱点标签。

### Case-Driven 优化（2026-07-05）

本轮优化针对 verbose E2E 失败样本推进，没有放宽评估规则：

- `finish_score_pass`：补充规则评分器的强业务信号识别。对“保单贷款/临时资金/灵活交费”“赎回/市场波动/本金可能亏损”“监管要求/不能承诺收益/风险偏好”等高质量回答给出合理分数。
- `weak_tag_pass`：信息过载与强推销改为独立业务风险开关。长篇堆参数回答稳定命中“信息过载、重点不突出”，施压式异议处理稳定命中“异议处理不当、客户关系不佳、强推销”。
- `retrieval_hit`：客户侧 RAG 在识别“肯定赚钱、稳赚、保证收益、写进合同”等合规敏感表达时，强制加入 `compliance_sensitive` query rewrite，确保召回风险说明和合规揭示上下文。
- `finish_score_pass` 校准：当主 rubric 覆盖率为 0 且不是强业务处理场景时，分数保持中等上限，避免普通回答被过度抬高；对缺少“历史不代表未来/说明书依据”的历史年化收益话术增加收益说明风险约束。
- `50-case` 扩展：继续新增保本拒绝、最高收益区间说明、合同边界、直接推荐拒绝、老年客户流动性、费用敏感、赎回到账、专业术语过载、只讲流程不讲风险、只共情不讲产品、低风险客户错配高风险产品等回归用例。
- `fallback` 稳定性：当向量索引或 sentence-transformers 不可用时，JSON lexical fallback 也会对合规敏感和异议处理 query 做轻量扩展，避免新同事 Docker/本地首次启动时 retrieval_hit 偏低。

### 评测规则更新（2026-07-04）

#### retrieval_hit 收紧规则
- **旧规则**：只要返回 items 就算通过
- **新规则**：
  - reply 使用 `expected_customer_evidence` 检查 customer route
  - finish 使用 `expected_tutor_evidence` 检查 tutor route
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
  - 评分输出与评估共用 `weakness_taxonomy` 标准词表和显式 alias
  - 不再允许无关标签仅凭两个汉字重叠通过
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

- **50 条测试用例**，扩展覆盖：
  - **合规红线场景**（10+ 条）：
    - 保本保息承诺
    - 绝对保本/稳赚
    - 收益写进合同
    - 明确表示没风险
    - 软性收益误导
    - 内部消息违规
    - 大平台不会亏
    - 跳过适当性测评
    - 低风险客户错配高风险产品
    - 多轮对话后续回退到承诺收益
  - **好回答场景**（20+ 条）：
    - 明确风险揭示
    - 不承诺收益
    - 有适当性管理
    - 共情理解客户
    - 根据风险承受能力推荐
    - 尊重家庭决策
    - 费用/退保说明
    - 办理流程和材料说明
    - 最高收益区间说明
    - 合同边界解释
    - 老年客户流动性建议
    - 赎回到账说明
    - 基金产品差异化说明
  - **中等回答场景**（6 条）：
    - 讲了风险但不完整
    - 讲了流程但缺少引导
    - 信息过载缺乏重点
    - 多轮修正（第一轮踩红线后纠正）
    - 只讲流程但缺风险收益
    - 只共情但缺产品信息
    - 合规但缺成交引导
  - **异议处理场景**（4 条）：
    - 灵活性异议（好回答）
    - 犹豫异议（强推销回答）
    - 家庭商量异议（尊重客户）
    - 家庭商量异议（施压成交）
  - **电话邀约场景**（2 条）：
    - 明确邀约
    - 施压邀约

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
