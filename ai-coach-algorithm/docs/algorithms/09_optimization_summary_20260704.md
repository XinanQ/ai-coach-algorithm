# AI Coach Algorithm 优化总结 (2026-07-04)

## 优化目标

**核心目标**：建立真实端到端评测闭环，并基于失败 case 做系统性优化，目标是让"完整陪练流程"的正确率明显提升。

## 本次改动总览

### 新增文件

| 文件 | 说明 |
|------|------|
| `eval/stages/eval_e2e.py` | E2E 评测入口模块 |
| `eval/stages/_eval_e2e_impl.py` | E2E 评测实现（lazy load） |
| `data/eval/e2e_dialog_gold.jsonl` | E2E 测试数据集（20条用例） |
| `docs/algorithms/08_e2e_evaluation.md` | E2E 评测文档 |
| `docs/algorithms/09_optimization_summary_20260704.md` | 本总结文档 |

### 修改文件

| 文件 | 主要改动 |
|------|----------|
| `eval/run_all.py` | 新增 e2e 评测到默认阶段，E2E 使用全部 gold |
| `app/core/marketing_rag.py` | RAG v7: MMR 多样性 + context pack 支持 |
| `app/core/dialog_manager.py` | 环境变量控制 context pack、重复追问修复 |
| `app/core/coverage.py` | Negative pattern + partial coverage 支持 |
| `eval/stages/eval_llm_intent.py` | LLM intent prompt 优化 |
| `eval/stages/eval_retrieval.py` | 新增 recall@5/8, context_hit@5/8 指标 |
| `eval/stages/_eval_e2e_impl.py` | E2E 评测收紧：retrieval/followup/weak_tag/score 严格验证 |
| `README.md` | 新增 E2E 评测说明 |
| `docs/algorithms/07_rag_evaluation.md` | 更新反映 v7 架构 |

## 优化优先级与成果

### 第一优先级：收紧 E2E 评测 ✅

**目标**：让 E2E 评测更接近真实业务正确率，避免虚假的高通过率。

**实现内容**：

1. **retrieval_hit 收紧**
   - **旧规则**：只要返回 items 就算通过
   - **新规则**：
     - 如果 `expected_must_points` 非空，必须命中至少一个关键词
     - 提取 `expected_must_points` 中的中文关键词（2+ 字符）
     - 检查 top-5 检索结果的 content/title 是否包含关键词
     - 如果 `expected_must_points` 非空但无任何命中 → FAIL

2. **followup_pass 收紧**
   - **旧规则**：文本长度 > 3 就放行
   - **新规则**：
     - 必须匹配 gap intent 的关键词 或 expected_followup_direction 的关键词
     - 扩展 intent 关键词表（每个 intent 5-7 个关键词）
     - 如果没有任何关键词匹配 → FAIL
     - 禁止单纯靠长度放行

3. **weak_tag_pass 收紧**
   - **旧规则**：未检测到标签也算通过
   - **新规则**：
     - 如果 `expected_weak_tags` 非空，必须检测到至少一个相关标签
     - 支持 2-4 字符子串匹配
     - 如果 `expected_weak_tags` 非空但 `weak_tags` 为空 → FAIL

4. **finish_score_pass 校准**
   - **旧规则**：gold 中的评分区间校准不足
   - **新规则**：
     - 合规红线：0-40 分
     - 中等回答：50-75 分
     - 好回答：80-98 分
     - 重新校准所有 gold 的 `expected_score_range`

5. **详细 failure trace**
   - 新增 `_build_failure_trace()` 方法
   - 输出失败阶段、expected vs actual、检索 top items、followup_message、score/weak_tags

**成果**：
- E2E 评测从 smoke test 升级为严格的业务正确率评估
- 当前 E2E overall_pass: 0.0 (收紧前为 1.0)
- 能够真实反映系统的端到端质量问题

### 第二优先级：RAG Context Pack 进入主链路 ✅

**目标**：让主链路真正吃到 final_k > 3 的收益。

**实现内容**：

1. **环境变量控制**
   - 新增 `AI_COACH_REPLY_CONTEXT_K`，默认 5
   - 新增 `AI_COACH_FINISH_CONTEXT_K`，默认 8

2. **主链路调用更新**
   - `reply_dialogue()`: 使用 `_REPLY_CONTEXT_K`
   - `reply_dialogue_stream()`: 使用 `_REPLY_CONTEXT_K`
   - `finish_dialogue()`: 使用 `_FINISH_CONTEXT_K`

3. **backward compatible**
   - 保持 `top_k` 参数向后兼容
   - `retrieve_marketing_knowledge()` 自动处理 `final_k`

**成果**：
- 主链路现在使用 final_k=5 (reply) 和 final_k=8 (finish)
- retrieval_trace 中可见 `final_k` 和 `selection_method`
- Docker 环境仍可用（环境变量可配置）

### 第三优先级：修复重复追问检测 ✅

**目标**：修复中文关键词匹配 bug，避免重复追问。

**实现内容**：

1. **intent -> 中文关键词表**
   - 新增 `INTENT_KEYWORDS_ZH` 字典
   - 每个 intent 映射到 5-7 个中文关键词
   - 例如：rate_concern → ["收益", "利率", "分红", "划算", "利息", "高", "多少"]

2. **重写 `_is_asking_about_same_topic()`**
   - 使用关键词匹配代替字符遍历
   - 统计匹配的关键词数量
   - 对于 intents 有 3+ 关键词的，至少匹配 2 个才算重复
   - 对于 intents 有较少关键词的，至少匹配 1 个

**成果**：
- 修复了中文关键词匹配 bug
- 重复追问检测现在能正确工作
- E2E trace 中会记录重复追问避免情况

### 第四优先级：扩充和校准 E2E Gold ✅

**目标**：从 7 条扩展到至少 20 条，覆盖更多场景。

**实现内容**：

1. **扩展到 20 条用例**
   - 合规红线场景：5 条（保本保息、绝对保本、收益写进合同等）
   - 好回答场景：6 条（全面风险揭示、适当性管理、共情理解）
   - 中等回答场景：6 条（部分风险揭示、办理流程缺失、多轮修正）
   - 异议处理：2 条（灵活性异议、犹豫异议）
   - 电话邀约：1 条

2. **评分区间校准**
   - 合规红线：0-40 分
   - 信息不足：20-40 分
   - 中等回答：40-65 分
   - 中等偏上：50-75 分
   - 好回答：75-95 分

**成果**：
- E2E gold 数据从 7 条扩展到 20 条
- 覆盖类型更加全面
- 评分区间更符合业务预期

### 第五优先级：同步 Report 和文档 ✅

**目标**：更新 report 和文档，确保一致性。

**实现内容**：

1. **运行完整 eval**
   - `python -m eval.run_all --stages all`
   - 生成最新的 `data/eval/report.json`

2. **更新文档**
   - `docs/algorithms/08_e2e_evaluation.md`: 反映收紧后的评测规则
   - `docs/algorithms/09_optimization_summary_20260704.md`: 更新优化总结
   - `README.md`: 确保运行说明准确

**成果**：
- report.json 包含最新数据
- 文档与实际 eval 输出一致
- 不再夸大 E2E 通过率

### 第六优先级：验证和回归 ✅

**目标**：确保改动不破坏现有功能。

**验证内容**：

1. **语法检查**
   - 所有 Python 文件语法正确
   - 模块导入无错误

2. **功能验证**
   - `/dialog/reply` 不返回 `liveScore/source`
   - `/dialog/finish` 正常返回 `score/source`
   - `reply/stream` 不被破坏
   - JSON fallback 仍可用
   - Docker 配置不受影响

3. **回归测试**
   - E2E eval 运行正常
   - run_all 运行正常

**成果**：
- 所有验证通过
- 接口契约未被破坏
- 兼容性保持完好

## 指标变化总结表

### 优化前（初始状态）

| 指标 | 数值 |
|------|------|
| e2e_overall_pass | 1.0 (过松) |
| contract_pass | 1.0 |
| intent_pass | 1.0 |
| gap_pass | 1.0 |
| retrieval_hit | 1.0 |
| followup_pass | 1.0 |
| finish_score_pass | 0.0 |
| weak_tag_pass | 0.0 |
| E2E gold size | 7 |

### 优化后（收紧评测）

| 指标 | 数值 | 说明 |
|------|------|------|
| e2e_overall_pass | 0.0 | 收紧后更真实 |
| contract_pass | 1.0 | 契约完全符合 |
| intent_pass | 1.0 | 意图检测正常 |
| gap_pass | 1.0 | Gap 计算正确 |
| retrieval_hit | 0.2 | 检索需要改进 |
| followup_pass | 1.0 | 追问方向正确 |
| finish_score_pass | 0.15 | 评分校准需改进 |
| weak_tag_pass | 0.85 | 标签检测较好 |
| E2E gold size | 20 | 扩展到 20 条 |

### RAG 指标（保持稳定）

| 指标 | 数值 | 说明 |
|------|------|------|
| candidate_recall@20 | 0.9020 | 候选召回优秀 |
| reranked_recall@3 | 0.5679 | Top3 召回中等 |
| reranked_recall@5 | 0.6849 | Top5 召回较好 |
| reranked_recall@8 | 0.7693 | Top8 召回良好 |
| context_hit@5 | 1.0 | 上下文命中优秀 |
| context_hit@8 | 1.0 | 上下文命中优秀 |

### 其他核心指标

| 指标 | 数值 | 说明 |
|------|------|------|
| llm_only_micro_f1 | 0.7576 | LLM 意图检测 |
| gap accuracy | 0.9481 | Gap 计算准确 |
| must_point point_f1 | 0.8299 | 必讲点覆盖优秀 |

## 当前问题根因分析

### 主要问题

1. **retrieval_hit: 0.2**
   - **根因**：`expected_must_points` 关键词提取不准确，或检索确实未覆盖相关知识
   - **影响**：16/20 用例检索验证失败
   - **修复方向**：
     - 改进关键词提取算法
     - 增加 candidate_k 或优化 rerank
     - 检查 gold 中的 `expected_must_points` 是否合理

2. **finish_score_pass: 0.15**
   - **根因**：评分系统与校准后的 gold 区间不匹配
   - **影响**：17/20 用例评分不在预期区间
   - **修复方向**：
     - 调整评分算法（rule_scorer 或 llm_scorer）
     - 重新校准 gold 的评分区间
     - 分析具体失败 case 的实际得分分布

3. **e2e_overall_pass: 0.0**
   - **根因**：retrieval_hit 和 finish_score_pass 拖累整体通过率
   - **影响**：所有用例都不通过综合评估
   - **修复方向**：优先解决 retrieval 和 scoring 问题

## 次要问题

1. **gold 数据质量**
   - 部分用例的 `expected_must_points` 可能不够准确
   - 部分用例的 `expected_score_range` 可能需要微调

2. **关键词提取**
   - 当前使用简单的 2+ 字符分割
   - 对于复杂的中文短语可能不够准确

## 下一步建议

### 短期（1-2 周）

1. **修复 retrieval_hit**
   - 分析 16 个失败用例的检索结果
   - 优化关键词提取算法
   - 考虑增加 final_k 或 candidate_k
   - 目标：retrieval_hit > 0.5

2. **修复 finish_score_pass**
   - 分析 17 个失败用例的实际得分
   - 调整评分算法或 gold 区间
   - 目标：finish_score_pass > 0.6

3. **优化 gold 数据**
   - 人工 review 20 条用例
   - 调整 `expected_must_points` 和 `expected_score_range`
   - 目标：gold 数据更准确

### 中期（1-2 月）

1. **扩展 E2E gold**
   - 从 20 条扩展到 50 条
   - 覆盖更多场景和边界情况
   - 目标：E2E gold 更全面

2. **优化 RAG 召回**
   - 参数调优（MMR lambda、rerank weights）
   - 考虑增加场景特定 boost
   - 目标：reranked_recall@5 > 0.75

3. **CI 集成**
   - 每次 PR 自动运行 E2E subset
   - 禁止 E2E 通过率下降的合并
   - 目标：持续监控质量

### 长期（3-6 月）

1. **提升 E2E 通过率**
   - 从当前的 0% 提升到 40%+
   - 系统性修复短板
   - 目标：E2E overall_pass > 0.4

2. **根因分析自动化**
   - 失败 case 自动分类
   - 指向上游模块并提供建议
   - 目标：快速定位问题

3. **真实业务对齐**
   - 与实际陪练数据对比
   - 校准 E2E 预期分数区间
   - 目标：更接近真实业务表现

## 风险与回退方案

### 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| E2E 评测过严导致大量失败 | 开发士气受挫 | 低 | 分阶段修复，优先高价值场景 |
| RAG context pack 增加延迟 | 回复速度变慢 | 低 | 轻量级 MMR，控制 final_k 大小 |
| 评分校准不准确 | finish_score_pass 持续低 | 中 | 人工 review gold，迭代校准 |
| Gold 数据质量问题 | 评测不稳定 | 中 | 扩充 gold 并人工验证 |

### 回退方案

1. **E2E 评测回退**
   - 使用之前的宽松规则（只要返回 items 就算通过）
   - 在 `_eval_e2e_impl.py` 中恢复旧逻辑

2. **RAG final_k 回退**
   - 设置环境变量 `AI_COACH_REPLY_CONTEXT_K=3`
   - 设置环境变量 `AI_COACH_FINISH_CONTEXT_K=3`

3. **评分校准回退**
   - 恢复旧的 gold 数据
   - 在 `data/eval/e2e_dialog_gold.jsonl` 中回退

## 验证要求

### 必跑验证

```bash
# 1. E2E 评测（全部 gold）
python -m eval.run_all --stages e2e

# 2. RAG 评测
python -m eval.stages.eval_retrieval --verbose

# 3. 完整评测
python -m eval.run_all --stages all
```

### 契约验证

1. 确认 `/dialog/reply` 不返回 `liveScore/source`
2. 确认 Docker 环境仍可用
3. 确认 JSON fallback 仍可用

## 涉及文件列表

### 新增（5 个文件）

1. `eval/stages/eval_e2e.py`
2. `eval/stages/_eval_e2e_impl.py`
3. `data/eval/e2e_dialog_gold.jsonl` (从 7 条扩展到 20 条)
4. `docs/algorithms/08_e2e_evaluation.md`
5. `docs/algorithms/09_optimization_summary_20260704.md`

### 修改（9 个文件）

1. `eval/run_all.py` - E2E 使用全部 gold
2. `app/core/marketing_rag.py` - RAG v7 架构
3. `app/core/dialog_manager.py` - 环境变量、重复追问修复
4. `app/core/coverage.py` - Negative pattern 支持
5. `eval/stages/eval_llm_intent.py` - Prompt 优化
6. `eval/stages/eval_retrieval.py` - 新指标
7. `README.md` - E2E 说明
8. `docs/algorithms/07_rag_evaluation.md` - v7 架构
9. `docs/algorithms/08_e2e_evaluation.md` - 收紧规则说明

## 结论

本次优化聚焦于建立真实可靠的端到端评测闭环，主要成果包括：

1. **收紧 E2E 评测**：从 smoke test 升级为严格的业务正确率评估
2. **RAG Context Pack**：主链路使用 final_k=5/8，提升检索质量
3. **修复重复追问**：中文关键词匹配 bug 修复
4. **扩充 E2E Gold**：从 7 条扩展到 20 条，覆盖更多场景
5. **校准评分区间**：合规红线 0-40，好回答 80-95
6. **详细 failure trace**：便于根因分析

### 当前状态

- **E2E overall_pass**: 0.0 (收紧后的真实表现)
- **主要瓶颈**: retrieval_hit (0.2)、finish_score_pass (0.15)
- **核心优势**: 好的意图检测 (0.7576)、gap 计算 (0.9481)、must point 覆盖 (0.8299)

### 下一步重点

1. 修复 retrieval_hit（关键词提取、RAG 参数调优）
2. 修复 finish_score_pass（评分算法校准）
3. 优化 gold 数据质量
4. 持续提升 E2E 通过率

本次优化建立了真实的评测基准，为后续系统性改进指明了方向。