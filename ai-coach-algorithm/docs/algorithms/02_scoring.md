# 算法文档 02 — 评分系统

> 涉及代码:[app/core/rule_scorer.py](../../app/core/rule_scorer.py) + [app/core/llm_scorer.py](../../app/core/llm_scorer.py) + [app/core/llm/schemas.py](../../app/core/llm/schemas.py)

## 1. 核心问题

陪练评分需要满足三个互相冲突的要求:

| 要求 | 含义 | 冲突点 |
|---|---|---|
| **可解释** | 老员工看分要能复盘"为什么扣分" | 单一总分无法做到 |
| **可控制** | 合规问题永远不能给高分 | 一刀切又会误伤好的回答 |
| **细粒度** | 不同维度独立反馈,定向改进 | 增加判断难度 |

**解法:4 维度评分模型 + LLM 优先评分 + 规则评分兜底**。

## 2. 4 维度评分模型

定义在 `rule_scorer.DIMENSION_DEFS`,LLM 和 Rule 共享:

| key | 中文 | 权重 | 看什么 | 数据来源 |
|---|---|---|---|---|
| `compliance` | 合规度 | 30% | 是否踩 `compliance_red_lines` | criterion 红线词表 |
| `objection_handling` | 异议处理 | 30% | `must_points` 覆盖率 | criterion 标准要点 |
| `logic_structure` | 逻辑结构 | 20% | 60% 覆盖率 + 40% 检索语义贴合 | coverage + 检索结果 |
| `empathy` | 共情力 | 20% | 共情词命中 + 引导词奖励 | 文本分析 |

**总分** = Σ(dim_score × weight),夹在 0-100。

修改维度的入口:`rule_scorer.DIMENSION_DEFS`。改 key/name/weight 会自动同步到 LLM prompt 和 presenter 输出,**不需要改其他地方**。

## 3. 评分路径选择

> **重要:评分只在 finish 阶段发生。** 每轮 reply 的实时评分(liveScore)已下线——
> 为降低高并发下的 token 消耗,分数只在训练结束时基于完整对话计算一次。reply 阶段
> 只生成客户追问,不评分。详见 §4.2。

```
        dialog_manager._score_finish   ← 仅 finish 调用
                          │
              ┌───────────┴────────────┐
              │ AI_COACH_SCORER=?       │
              └───────────┬────────────┘
                  llm     │     rule
                  ↓                ↓
         llm_scorer.score_*   rule_scorer.score_employee_answer
              │ ┌─ LLM 调用成功 → 返回
              │ │
              │ └─ 失败(no KEY/网络/Pydantic) ↓
              ↓
         rule_scorer.score_employee_answer  ← 自动兜底
              │
              ↓
         返回 score dict + method 字段
              │
              ↓
         presenter._source_from_method
              ↓
         source = "LLM_BASED" 或 "RULE_BASED"
```

`AI_COACH_SCORER` 环境变量(默认 `llm`)控制是否尝试 LLM。任何失败都静默回退到 rule_scorer——对 Java 后端透明,只有 source 字段会反映实际跑了哪个。

## 4. LLM 评分(主路径)

### 4.1 完整调用栈

```
score_with_llm_finish(answer, criterion, coverage, dialog_pairs)
       │
       ├─ get_finish_builder_for_scene(criterion, scene_id).to_chat_messages(context)
       │       ↓
       │   5 层 prompt → [system, user] messages
       │       ↓
       ├─ _call_with_retry(messages, method="finish", scene_id)
       │       │
       │       ├─ _call_llm_json_raw → LLM 返回 raw text
       │       │       │
       │       │       └─ retry.call_with_retry 包裹:429/5xx/timeout 退避 3 次
       │       │       └─ metrics.llm_call_tracker 记录 tokens/latency/cache hit
       │       │
       │       ├─ parser.parse_and_validate(raw, LLMScoreOutput)
       │       │       │
       │       │       ├─ json.loads → 失败 → json_repair.loads → 失败 → 代码块提取
       │       │       └─ Pydantic 校验:范围 0-100 + 内部一致性
       │       │
       │       ├─ 成功 → 返回 LLMScoreOutput
       │       └─ 失败但是 retry_candidate(JSON 解析 OK 但 Pydantic 失败)
       │              ↓
       │           重试一次,把错误反馈给 LLM 让它自修
       │
       └─ _shape_result → 转成 rule_scorer 兼容 dict
              ↓
       返回 { total_score, dimension_scores, weakness_tags, suggestion, method, ... }
```

### 4.2 finish 评分(reply 实时评分已下线)

评分只在 **finish** 阶段发生。早期版本每轮 reply 会算一个 liveScore 实时预览,
但在高并发下这意味着每轮都多一次 LLM/检索开销,而最终用户看到的分数仍以 finish
为准——收益不抵成本,故下线。**现在 reply 只生成客户追问,不评分**。

| | finish(最终评分) | ~~reply(已移除)~~ |
|---|---|---|
| 输入 | 完整对话 dialog_pairs + criterion + coverage | ~~仅本轮员工话~~ |
| Prompt | `get_finish_builder_for_scene(criterion, scene_id)`(完整 5+1 层) | — |
| 评估 | 看整体表现,认可纠错,红线一票否决 | — |
| 用途 | 训练结束的正式评分 | — |
| 延迟 | ~2-3s | — |

LLM 在 finish prompt 里能看到完整对话轨迹(`dialog_pairs` 由 `dialog_manager._build_dialog_pairs` 组装),所以可以识别"先犯错后挽救"这种模式。

> `llm_scorer.score_with_llm_reply` 函数仍保留(供将来需要时复用),但 `dialog_manager`
> 已不再调用它。reply 响应也不再返回 `liveScore` / `source` 字段。

### 4.3 Pydantic 校验:抓最严重的幻觉

`schemas.py.LLMScoreOutput` 定义校验规则,**核心是内部一致性检查**:

```python
@model_validator(mode='after')
def _internal_consistency(self):
    compliance = self.dimension_scores.get('compliance', 0)
    if compliance >= 85:
        # 抓"合规度 100 + weakTags 含合规风险"这种自相矛盾
        offending = [t for t in self.weakness_tags if '合规' in t or '风险' in t]
        if offending:
            raise ValueError(f"compliance={compliance} but tags={offending} — 矛盾")
        if any(self.risk_terms):
            raise ValueError(f"compliance={compliance} but risk_terms 非空 — 矛盾")
```

这是 LLM 幻觉的高频场景:模型评分时给了 95 分合规,但又顺手在 weakTags 写"合规风险"。**Pydantic 失败时不直接放弃,而是重试一次**(下一节)。

### 4.4 Per-scene builder + L2-Anchor(关键缓存优化)

每个 scene 一个独立的 builder 实例,scene rubric 被烤进 `ScorerSceneAnchorLayer` 静态层。**同一 scene 的所有评分调用共享同样的 prompt 前缀字节** → DeepSeek prompt cache 跨调用命中。

```python
# llm_scorer.py
from app.core.llm.prompts.scorer import get_finish_builder_for_scene

builder = get_finish_builder_for_scene(criterion, scene_id="INS_PERIODIC")
messages = builder.to_chat_messages({
    "answer": ..., "coverage": ..., "dialog_pairs": ...,
    # 注意:criterion 已经被烤进 builder 的静态层,这里不用再传
})
```

效果:同一 scene 跑 N 次评分,只有第 1 次"建立缓存",第 2 次起命中 — token 成本下降 60-70%。详见 [05_prompt_architecture.md §4.6](05_prompt_architecture.md)。

### 4.5 重试一次机制(自修)

`_call_with_retry` 区分两种失败:

| 失败类型 | parser.ParseResult | 处理 |
|---|---|---|
| LLM 没返回 / 网络挂 | None | 直接兜底 rule |
| LLM 返回不是 JSON | `is_retry_candidate=False` | 直接兜底(重试也没用,模型在乱说) |
| LLM 返回是合法 JSON 但违反 Pydantic | `is_retry_candidate=True` | **重试一次**,把错误反馈给 LLM |

重试时的 user 消息:

```
你上次返回的 JSON 违反了输出规范:
{具体错误,比如 "compliance=100 but weakness_tags contain ['合规风险']"}

请重新输出严格符合规范的 JSON。注意:
- 所有 dimension_scores 值必须是 0-100 的整数
- compliance ≥85 时,weakness_tags 不能包含'合规'相关条目,risk_terms 必须为空
- 只输出 JSON,不要任何前后缀文字
```

实测约 70%+ 的 Pydantic 失败,LLM 在重试时能自修。仍失败的才兜底到 rule。

## 5. Rule 评分(兜底路径)

`rule_scorer.score_employee_answer` 完全不调用 LLM,纯文本规则:

```python
# 每个维度按文本特征算分
compliance = _score_compliance(answer, red_lines)
   # 命中任何 red_line 直接扣 40,无命中给满分
objection = _score_objection(answer, coverage)
   # 有 coverage 时用 coverage_rate × 100,否则关键词粗估
logic = _score_logic(answer, coverage, retrieval_items)
   # 60% 覆盖率 + 40% 检索贴合度
empathy = _score_empathy(answer)
   # 共情词命中数 × 12 + 有引导词 +15

total = sum(dim_score × weight)
```

Rule 兜底的优势:
- 不依赖网络,永不超时
- 可解释性最强(任何分数都能追到具体词)
- LLM 失败时保证系统不挂

劣势:
- 关键词数数为主,语义判断弱
- 抓不到"软违规"(如包装成存款这种没踩字面红线的)
- suggestion 是固定模板

## 6. 输出 dict 结构(LLM 和 Rule 完全一致)

```python
{
  "total_score": 78,                         # 0-100 加权总分
  "dimension_scores": [                       # 4 维度展开
    {"key": "compliance", "name": "合规度", "score": 90, "weight": 0.3},
    {"key": "objection_handling", "name": "异议处理", "score": 70, "weight": 0.3},
    {"key": "logic_structure", "name": "逻辑结构", "score": 75, "weight": 0.2},
    {"key": "empathy", "name": "共情力", "score": 65, "weight": 0.2},
  ],
  "matched_terms": [...],                    # 命中的良好话术词
  "risk_terms": ["稳赚"],                    # 命中的合规敏感词
  "missing_points": ["说明分红不确定性"],     # 漏答的标准要点
  "weakness_tags": ["合规风险", "共情缺失"], # 弱点标签
  "suggestion": "...",                       # 自然语言改进建议
  "intent_understanding": {...},             # 意图识别快照
  "method": "llm_scorer_deepseek_finish",    # ← 给 presenter 判 source 用
}
```

`method` 字段用前缀区分:`llm_scorer_*` → presenter 返回 `LLM_BASED`,其他 → `RULE_BASED`。

## 7. 调优入口速查

| 想改什么 | 改哪里 |
|---|---|
| 维度 key/名字/权重 | `rule_scorer.DIMENSION_DEFS`(LLM 自动同步) |
| 合规度扣分力度(每命中一条扣多少) | `rule_scorer._score_compliance` 里的 `100 - len(hits) * 40` |
| 共情词词表 | `rule_scorer.EMPATHY_TERMS` |
| 引导词词表 | `rule_scorer.GUIDANCE_TERMS` |
| 全局合规红线(场景红线之外的兜底) | `rule_scorer.HIGH_RISK_TERMS` |
| 良好话术词 | `rule_scorer.GOOD_PRACTICE_TERMS` |
| LLM 评分 prompt 任一层 | `app/core/llm/prompts/scorer.py` |
| LLM 评分硬约束(L4) | `app/core/llm/prompts/boundaries.py` `ScorerBoundaryLayer` |
| Pydantic 内部一致性规则 | `app/core/llm/schemas.py` `LLMScoreOutput._internal_consistency` |
| 重试时给 LLM 的纠错提示 | `llm_scorer._call_with_retry` 第 162-175 行 |
| 切换 LLM/Rule | `AI_COACH_SCORER=llm|rule` 环境变量 |

## 8. 失败回退矩阵

| 失败点 | 兜底 | source 字段返回 |
|---|---|---|
| 无 `DEEPSEEK_API_KEY` | rule_scorer | `RULE_BASED` |
| LLM 网络超时 / 5xx | retry 3 次,失败后 rule | `RULE_BASED` |
| LLM 429 限流 | 退避 3 次,失败后 rule | `RULE_BASED`,metrics 标 rate_limited |
| LLM 返回非 JSON | json-repair / 代码块提取 | 通常救活,透明 |
| LLM 返回 JSON 但内部矛盾 | 重试一次让 LLM 自修 | 70%+ 救活 |
| Pydantic 重试也失败 | rule_scorer | `RULE_BASED` |
| 整个 LLM 子系统挂 | rule_scorer,系统仍能跑 | `RULE_BASED` |

**核心承诺:任何 LLM 失败 → 静默回退 rule,不报 500**。Java 后端只有看 source 字段才知道发生过降级。

## 9. 已知限制与待办

| 问题 | 现状 | 路径 |
|---|---|---|
| Rule scorer 抓不到软违规 | 已知 | LLM 评分能抓,优先保 LLM 可用率 |
| 维度权重经验值,未在数据上校准 | 已知 | 需要 gold 评分集做权重调优 |
| 无 LLM 评分回归测试集 | 已知 | 攒 30 条 gold 对话,每次 prompt 改完跑 |
| LLM 评分分布偏严(尤其 empathy) | 已知 | 调 L3 instruction 的"标准要点 ≥50%"门槛 |
| 对话过程中无实时分数反馈 | 设计取舍(为省 token 下线了 reply 评分) | 如需恢复:dialog_manager 重新接 `score_with_llm_reply` |

## 10. 演示亮点(怎么让别人看到价值)

1. **对话里故意踩 5 个合规雷** → finish 最终分被合规红线一票否决,降到 20 左右 → LLM 评分能抓到的合规问题,rule 完全抓不住
2. **finish 的 suggestion** → LLM 写的自然语言诊断,而不是模板套话
3. **改 `AI_COACH_SCORER=rule`** → 同样的回答 LLM 评 21 分(合规度 0),rule 评可能 50+(因为没抓到"跟存款一样"这种软违规)
4. **/metrics/llm** → 看 LLM 评分调用的 token / 缓存命中,证明系统真在工作而不是 mock
