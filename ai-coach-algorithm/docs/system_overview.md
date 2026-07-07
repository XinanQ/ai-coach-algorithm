# AI 陪练算法服务 — 完整说明文档

> 适用版本:阶段 1-3 + 记忆升级(Layer 1-3) + Docker 开发环境完成后
> 适用读者:接手该服务的算法开发、对接的 Java 后端、做 demo 的产品同事

---

## 1. 系统定位

金融绩效驱动 AI 陪练系统的**算法服务层**。独立 Python FastAPI 服务,负责:

- **AI 客户模拟**:LLM 扮演真实客户,与员工进行多轮陪练对话
- **员工答案评分**:基于场景 rubric + LLM 评委,输出 4 维度评分 + 改进建议
- **双路 RAG 检索**:导师侧锚定标准要点检索 / 客户侧基于意图 gap 检索
- **历史感知训练**:聚合用户弱点画像,AI 客户针对弱项施压,评分器关注改善
- **向量化记忆检索**:ChromaDB 语义检索替代关键词匹配,精准召回相关训练记录
- **自适应难度**:根据历史成绩自动推荐训练难度(低/中/高),匹配对应客户画像

**核心设计原则:** 算法做识别和检测(意图、gap、检索),LLM 做生成和判断(评分、客户模拟)。两者协同,算法提供结构化辅助信号,LLM 做最终决策。

不在算法服务里的(在 Java 后端):用户鉴权、taskId 映射、积分认证、UI 联调。算法服务只对内提供 HTTP 调用,不接触用户态。

---

## 2. 整体架构

```text
                       ┌──────────────────────────────────────┐
                       │  Java 后端 (kw-Jak 仓库)             │
                       │  /api/mini/practice/dialog/*         │
                       │  - 鉴权 / taskId 映射 / 积分认证      │
                       └────────────────┬─────────────────────┘
                                        │ HTTP 内网调用
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                  Python 算法服务 (本仓库)                                  │
│                  FastAPI: /dialog/start /reply /finish + /metrics/llm     │
│                                                                            │
│  ┌──────────────┐   ┌──────────────────────┐    ┌─────────────────────┐  │
│  │  Presenter   │ ← │   Dialog Manager     │ ←→ │   Memory Manager    │  │
│  │  (camelCase  │   │   - 轮次控制         │    │   - Redis 短期      │  │
│  │   适配联调)  │   │   - gap/intent       │    │   - PG 长期         │  │
│  └──────────────┘   │   - 异步并行调用     │    │   - JSON 兜底       │  │
│                     │   - 弱点画像注入     │    │   - ChromaDB 向量   │  │
│                     │   - 自适应难度选择   │    │   - 弱点画像聚合    │  │
│                     └──────────┬───────────┘    └─────────────────────┘  │
│                                │                                          │
│                ┌───────────────┼───────────────┐                          │
│                ▼               ▼               ▼                          │
│    ┌──────────────────┐ ┌──────────────┐ ┌──────────────────────────┐    │
│    │  Marketing RAG   │ │ Rule Scorer  │ │      LLM 子系统          │    │
│    │  - 导师 HyDE     │ │ (规则评分,   │ │  - llm_scorer (评分)     │    │
│    │  - 客户 gap+     │ │  4 维度兜底) │ │  - llm_customer (模拟)   │    │
│    │  - Chroma 检索   │ └──────────────┘ │  - prompts/* (5 层架构)  │    │
│    └──────────────────┘                  │  - parser/schemas/retry  │    │
│              │                            │  - metrics (可观测性)    │    │
│              ▼                            └────────────┬─────────────┘    │
│    ┌──────────────────┐                                │                  │
│    │  Coverage / Gap  │                                ▼                  │
│    │  共享模块        │                    ┌───────────────────────┐      │
│    └──────────────────┘                    │  AsyncOpenAI 客户端   │      │
│                                            │  → DeepSeek API       │      │
│                                            └───────────────────────┘      │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 数据流:start → reply → finish 完整链路

### 3.1 `/dialog/start`(同步,零 LLM 调用)

轮次策略：公开 start 请求不再接收手动轮次数，避免调用方指定轮次造成联调口径混乱。算法根据 `taskId -> scene/customer/difficulty/direction`、客户画像 `expected_intents` 和训练方向自动推荐 6-10 轮，并在响应中返回 `totalRounds / minRounds / targetRounds / maxRounds / roundPolicy`。

```
Java → start(taskId, scene_id, difficulty?)
   ↓
recommend_difficulty(user_id, scene_id) → 推荐难度(Layer 3)
   ↓
get_customer_profile(scene_id, difficulty=推荐) → 加载对应难度画像
   ↓
build_weakness_profile(user_id, scene_id) → 弱点画像(Layer 1)
   ↓
session = { round=1, effective_rounds=N, difficulty_level, weakness_profile, ... }
   ↓
upsert_session → 写记忆
   ↓
presenter.present_start → 返回 camelCase
```

返回字段:`sessionId / taskId / round / totalRounds / difficultyLevel / difficultyRecommendation / messages[0].content(开场白)`

### 3.2 `/dialog/reply`(异步,1 个 LLM 调用:仅客户追问)

```
Java → reply(session_id, employee_message)
   ↓
analyze_customer_answer(employee_message)
   - 关键词意图打分(BERT 当前禁用,纯 keyword)
   ↓
update_covered_intents → covered_intents
compute_intent_gap(expected, covered) → gap_intents
   ↓
retrieve_marketing_knowledge(route="customer", focus_intents=gap)
   - 客户侧 RAG:embedding 检索 + 关键词融合 + gap 改写 query
   ↓
generate_customer_question_with_llm(profile, gap, retrieval, history)
   → 自然的 in-character 客户追问(reply 阶段唯一的 LLM 调用)
   ↓
末轮判断:current_round >= effective_rounds → finished=True,message=null
   (末轮跳过 RAG 检索和追问生成,直接交给 finish)
   ↓
presenter.present_reply → 返回 camelCase
```

返回字段:`round / totalRounds / message{role,content} / finished`

> 注:reply 实时评分(liveScore)已下线以省 token,分数只在 finish 计算。详见
> [algorithms/02_scoring.md §4.2](algorithms/02_scoring.md)。

### 3.3 `/dialog/finish`(异步,1 个 LLM 调用)

```
Java → finish(session_id)
   ↓
聚合所有 employee_messages(完整对话,不只末两段)
build_dialog_pairs → [{customer_question, employee_answer}, ...]
   ↓
get_primary_criterion(scene_id) → 加载 rubric(must_points / red_lines)
   ↓
retrieve_marketing_knowledge(route="tutor", must_points=criterion.must_points)
   - 导师侧 HyDE:用 must_points 锚定假设理想答案 → 检索
   - 同时计算 must_point_coverage(关键词+语义)
   ↓
score_with_llm_finish(answer, criterion, coverage, dialog_pairs)
   - 完整对话 + rubric + RAG 检索 → LLM 综合评分
   - 失败回退 rule_scorer
   ↓
写 session(status=finished) + 写长期记忆(longterm_memory)
   ↓
presenter.present_finish → 返回 camelCase + 业务字段 mock
```

返回字段:`score / dimensionScores / weakTags / suggestion / source` + 业务 mock(`resultId / scoreDelta / rewardPoints / certificationTitle` 等)

---

## 4. 模块组织

```
app/
├── main.py                            FastAPI app + 路由注册
├── api/                               接口层(presenter + route)
│   ├── dialog_api.py                  /dialog/start /reply /finish
│   ├── dialog_presenter.py            算法 dict → 联调 camelCase 适配
│   ├── memory_api.py                  /memory/*(short/long-term 操作)
│   ├── metrics_api.py                 /metrics/llm(可观测)
│   ├── rag_api.py                     /rag/marketing/*(检索调试)
│   └── tutor_api.py                   /marketing-tutor/prompt-context
├── core/                              核心算法
│   ├── dialog_manager.py              对话编排(start/reply/finish + 异步并行)
│   ├── marketing_rag.py               双路 RAG:导师 HyDE + 客户 gap
│   ├── coverage.py                    共享 coverage / gap 计算
│   ├── customer_answer_understanding.py   意图统一入口(关键词)
│   ├── customer_profile_loader.py     客户画像加载
│   ├── scoring_criteria_loader.py     场景 rubric 加载
│   ├── chroma_vector_store.py         Chroma 持久化向量库
│   ├── embedding_adapter.py           embedding 切换(bge-zh / hash 兜底)
│   ├── embedding_builder.py           向量库构建
│   ├── rule_scorer.py                 规则评分(4 维度,LLM 失败兜底)
│   ├── llm_scorer.py                  LLM 评分(async, finish + reply)
│   ├── llm_customer.py                LLM 模拟客户(async)
│   ├── intent_labels.py               6 个意图标签 + 关键词词表
│   ├── intent_*.py                    意图标注 / 标定 / 训练 / 评测
│   ├── bert_mini_*.py                 BERT-mini 适配器 / 训练器(当前禁用)
│   ├── memory_manager.py              短/长期记忆统一管理
│   ├── memory_store.py                Redis + PG + JSON 实现
│   ├── memory_vector_store.py         ChromaDB 向量索引(语义检索历史记忆)
│   ├── weakness_profile.py            弱点画像聚合(Layer 1,维度趋势 + 高频弱项)
│   ├── adaptive_difficulty.py         自适应难度推荐(Layer 3,自动升降难度)
│   ├── marketing_tutor_context.py     分层 prompt context(导师评分提示)
│   ├── text_cleaner.py                文本清洗工具
│   └── llm/                           LLM 子系统(阶段 1-3 新建)
│       ├── client.py                  AsyncOpenAI + sync 客户端工厂
│       ├── schemas.py                 Pydantic 输出模型 + 一致性校验
│       ├── parser.py                  3 层解析(json → json-repair → Pydantic)
│       ├── retry.py                   rate limit + 5xx 指数退避
│       ├── metrics.py                 结构化日志 + 进程级聚合
│       └── prompts/                   5 层 prompt 架构
│           ├── base.py                PromptLayer + LayeredPromptBuilder
│           ├── boundaries.py          L4 边界规则(反幻觉)
│           ├── formats.py             L5 输出格式 schema
│           ├── scorer.py              评分场景的 L1+L2+L3 + builder 工厂
│           └── customer.py            客户模拟场景的 L1+L2+L3 + builder 工厂
├── schemas/                           Pydantic 请求/响应模型
│   ├── dialog_schema.py
│   ├── memory_schema.py
│   ├── rag_schema.py
│   └── tutor_schema.py
└── utils/
    └── file_loader.py
data/
├── customer_profiles.json             39 个客户画像(14 场景 × 2-3 难度)
├── marketing_chunks.json              171 条话术 chunk(知识库)
├── marketing_scoring_criteria.json    31 条场景评分标准(rubric)
├── intent_eval_candidates.jsonl       178 条意图标注候选(193 已标 gold)
└── intent_eval_gold.jsonl             人工标注 gold 数据集
docs/
├── system_overview.md                 ← 本文档
├── backend_integration_guide.md       给 Java 后端的对接说明
└── intent_annotation_schema.md        意图标注规范
tests/
└── test_upgraded_embedding_memory_stack.py   端到端 API + RAG 测试
Dockerfile                                    算法服务镜像
docker-compose.yml                            开发联调:API + Redis + PostgreSQL
.dockerignore                                 镜像构建排除规则
```

---

## 5. 核心子系统

### 5.1 双路 RAG

**导师侧(`marketing_rag._retrieve_tutor_hyde`)**

| 步骤 | 做什么 |
|---|---|
| HyDE 锚定 rubric | 用 `criterion.must_points` 构造"假设理想答案",而不是员工原文(避免员工没说的内容永远检索不到) |
| 检索融合 | `0.72 × HyDE语义 + 0.23 × 原始query语义 + 0.05 × 关键词重合` |
| coverage 计算 | 对照每个 must_point 算覆盖率(关键词命中 + 余弦),输出 missing_texts |
| 阈值 | `TUTOR_MUST_POINT_THRESHOLD = 0.40`(临时值,待数据标定) |

**客户侧(`marketing_rag._retrieve_customer_intent_fusion`)**

| 步骤 | 做什么 |
|---|---|
| gap 驱动 query 改写 | 用 `gap_intents`(未覆盖顾虑)而不是员工原文做检索 query |
| 标签选择双阈值 | 绝对下限 `0.20` + 相对比例 `0.75 × top_score` 防过拟合 |
| 检索融合 | `0.58 × 意图改写query + 0.22 × 原始query + 0.10 × keyword + 0.06 × 关键词重合 + 0.04 × 意图匹配` |

### 5.2 LLM 层(阶段 1-3 重点)

**调用栈(自上而下):**

```
dialog_manager._score_finish / _next_customer_question
     ↓
llm_scorer.score_with_llm_finish
llm_customer.generate_customer_question_with_llm
     ↓
llm_scorer._call_with_retry(schema retry once)
     ↓
llm_scorer._call_llm_json_raw / _call_llm_text
     ↓ (llm/retry.py + llm/metrics.py 包裹)
     │   - retry policy: 429/5xx/timeout 退避 1s→2s→4s with jitter, max 3次
     │   - llm_call_tracker: 记录 tokens / latency / cache hit / errors
     ↓
AsyncOpenAI client → DeepSeek API
```

**输入处理:**

```
llm/prompts/base.LayeredPromptBuilder
     ↓
1. PersonaLayer (L1)        ← 静态,缓存
2. InstructionLayer (L3)    ← 静态,缓存
3. GlobalBoundary (L4)      ← 静态,缓存
4. SceneBoundary (L4)       ← 静态,缓存
5. FormatLayer (L5)         ← 静态,缓存
6. ContextLayer (L2)        ← 动态,每次重渲染
     ↓
to_chat_messages() → [{role:system, ...}, {role:user, ...}]
```

**输出处理:**

```
DeepSeek 返回 raw text
     ↓
parser.parse_json_lenient
   1. json.loads
   2. json_repair.loads   ← 修 trailing comma / 漏引号 / unicode 转义
   3. 提取 ```json ... ``` 代码块
     ↓
schemas.LLMScoreOutput.model_validate
   - 范围校验(0-100)
   - 内部一致性(合规度=100 + weakTags 含"合规" → 矛盾)
     ↓
失败时:_call_with_retry 把错误反馈给 LLM,重试一次
     ↓
成功:_shape_result 转成 rule_scorer 兼容的 dict 形态
```

### 5.3 评分

**4 维度评分模型**(`rule_scorer.DIMENSION_DEFS` 定义,LLM 也遵循):

| 维度 key | 中文名 | 权重 | 看什么 |
|---|---|---|---|
| `compliance` | 合规度 | 30% | 是否踩 `compliance_red_lines`(承诺收益/包装成存款/绝对化等) |
| `objection_handling` | 异议处理 | 30% | `must_point` 覆盖率(对照 rubric) |
| `logic_structure` | 逻辑结构 | 20% | 60% 要点覆盖 + 40% 检索语义贴合 |
| `empathy` | 共情力 | 20% | 共情词命中 + 引导词奖励 |

**总分 = Σ(dim_score × weight)**

**评分路径选择**(`dialog_manager._SCORER_PREFERENCE`):
- `AI_COACH_SCORER=llm`(默认):LLM 优先,失败/未配 KEY 自动回退 rule
- `AI_COACH_SCORER=rule`:跳过 LLM 直接走规则

**评分只在 finish 阶段发生**(reply 实时评分已下线以省 token):

| | finish(唯一评分点) |
|---|---|
| 输入 | 完整对话轨迹 + rubric + coverage + RAG |
| Prompt | 完整 builder(L2 含 dialog_pairs) |
| 评估 | 看整体表现,认可纠错,红线一票否决 |
| 用途 | 训练结束的正式评分 |

### 5.4 客户模拟

**5 层 prompt 在客户侧的体现:**

| 层 | 内容 |
|---|---|
| L1 系统人设 | 定义"扮演金融营销陪练客户"的最高准则 |
| L3 任务指令 | 决策树:合规风险 > gap 顾虑 > 全覆盖收尾 |
| L4 全局边界 | 反幻觉 / 反内部矛盾 / 禁多余文字 |
| L4 客户专属边界 | 禁 AI 腔 / 禁暴露 AI 身份 / 禁重复 |
| L5 输出形态 | 一到两句话 / ≤60 字 / 无前后缀 |
| L2 动态上下文 | 画像 + 对话历史 + 员工本轮话 + gap 列表 + RAG 检索话术 |

**算法辅助 LLM 的关键:**
- 算法识别 gap(`compute_intent_gap`)
- 算法做 RAG 检索(`retrieve_marketing_knowledge`)
- LLM 综合上下文 + 算法信号,生成自然追问

**回退路径:** LLM 失败 → 模板查表(`CUSTOMER_INTENT_PROBES`)

### 5.5 意图理解

**6 个标签** (`intent_labels.py`):

```
rate_concern              利率/收益/同业比较
liquidity_concern         提前支取/流动性/期限灵活
safety_concern            本金安全/风险/亏损
procedure_question        办理流程/材料/查询
rejection_or_hesitation   犹豫/拒绝/再考虑
compliance_sensitive      承诺/保证/最高收益等合规敏感表达
```

**当前状态:**
- BERT-mini 训练崩盘(F1=0 at epoch 5),已通过 `AI_COACH_BERT_MINI_FUSION=0` 禁用
- 系统纯走关键词打分(`keyword_intent_scores`)
- 阈值经标定回填:`update_covered_intents` 默认 `0.36`(从 0.05 升上来,193 条 gold 标定)
- 标注集:178 条候选,193 条已标 gold(包括手动补的 procedure_question)

### 5.6 共享 Coverage / Gap 模块

`coverage.py` 抽象了**"期望维度里员工答到了哪些、漏了哪些"**这件事,导师/客户两侧共用:

| | 导师侧 | 客户侧 |
|---|---|---|
| 期望维度 | `criterion.must_points`(话术要点) | `profile.expected_intents`(意图标签) |
| 覆盖判定 | `evaluate_coverage`:`0.4×keyword + 0.6×cosine` | `compute_intent_gap`:纯集合差 |
| 累积逻辑 | finish 时一次性算 | `update_covered_intents` 跨轮累积 |
| 用途 | 漏答扣分、检索锚点 | 驱动 LLM 追问 |

### 5.7 记忆(3 层架构)

| 层 | 主存储 | 兜底 | 作用 |
|---|---|---|---|
| 短期(session) | Redis | JSON 文件 | 单次对话上下文 |
| 长期(训练记录) | PostgreSQL | JSON 文件 | 训练历史,供弱点画像 + 难度推荐 |
| 向量索引(语义检索) | ChromaDB | lexical 关键词匹配 | 语义相似度查找相关训练记录 |

**新增模块:**
- **弱点画像**(`weakness_profile.py`):聚合用户最近 10 次训练,输出维度均值/趋势/高频弱项,注入 Prompt
- **向量记忆**(`memory_vector_store.py`):每条长期记忆生成 embedding,检索时用余弦相似度替代关键词匹配
- **自适应难度**(`adaptive_difficulty.py`):连续 3 次 ≥85 分升难度,连续 2 次 <60 分降难度

详见 [algorithms/06_memory_and_adaptive.md](algorithms/06_memory_and_adaptive.md)。

无 Redis / 无 PG / 无 ChromaDB 都能跑 demo,系统自动降级。

---

## 6. 5 层 Prompt 架构详解

### 设计原则

| 层 | 职责 | 静态/动态 | 反什么问题 |
|---|---|---|---|
| L1 系统人设 | 最高准则,身份框架 | 静态 | 模型角色混乱 |
| L2 上下文注入 | 动态业务数据 + 历史 | 动态 | 上下文缺失 |
| L3 核心指令 | 任务分解 + CoT 步骤 | 静态 | 任务执行跳步 |
| L4 边界规则 | 否定式硬约束 | 静态 | 幻觉 / 越界 |
| L5 输出格式 | 结构化 schema | 静态 | 格式不可解析 |

### 拼接顺序(prefix cache 友好)

```
system 消息:  L1
user 消息:    L3 → L4_global → L4_scene → L5 → L2(动态)
```

**为什么动态层放最后:** DeepSeek 按 byte 前缀做缓存匹配。把所有静态层往前堆,保证多次调用共享同样的开头,缓存命中后只按 10% 价格计费。

### LayeredPromptBuilder 行为

- 模块级单例:`_FINISH_BUILDER` / `_REPLY_BUILDER` / `_CUSTOMER_BUILDER` 在 import 时构造
- 静态层调用一次后写入 `_static_cache`,后续直接复用
- 动态层每次 `render(context)` 重渲染
- `to_chat_messages(context)` 直接返回可塞给 OpenAI SDK 的消息列表

### 修改 prompt 的入口

| 想改什么 | 改哪个文件 |
|---|---|
| 评分专家的身份描述 | `prompts/scorer.py` ScorerPersonaLayer |
| 客户角色框架 | `prompts/customer.py` CustomerPersonaLayer |
| 评分任务的 CoT 步骤 | `prompts/scorer.py` ScorerInstructionLayer |
| 反幻觉硬约束 | `prompts/boundaries.py` GlobalBoundaryLayer |
| 评分场景的扣分规则 | `prompts/boundaries.py` ScorerBoundaryLayer |
| 输出 JSON schema 描述 | `prompts/formats.py` ScorerFormatLayer |
| finish 看到的对话内容渲染 | `prompts/scorer.py` FinishContextLayer.render |

---

## 7. 接口契约

### 7.1 内部接口(算法侧)

| Method | Path | 用途 |
|---|---|---|
| GET | `/health` | 健康检查(向量库 / 记忆状态) |
| GET | `/dialog/profiles` | 列出 39 个客户画像(14 场景 × 多难度) |
| POST | `/dialog/start` | 开启对话,返回 sessionId + 开场白 + 难度推荐 |
| GET | `/dialog/difficulty-recommendation` | 查询难度推荐(Layer 3) |
| POST | `/dialog/reply` | 提交员工回复,返回 AI 客户追问(不再含实时评分) |
| POST | `/dialog/finish` | 结束对话,返回完整 4 维度评分 + suggestion |
| GET | `/metrics/llm` | LLM 调用聚合指标(tokens/cache hit/latency) |
| POST | `/metrics/llm/reset` | 清空 metrics(演示前用) |
| POST | `/rag/marketing/vector-index/build` | 重建向量库 |
| GET | `/rag/marketing/vector-index/status` | 向量库状态 |
| POST | `/rag/marketing/vector-retrieve` | 直接调用 RAG(调试用) |
| POST | `/rag/marketing/customer-answer-understanding` | 直接调用意图识别 |
| POST | `/marketing-tutor/prompt-context` | 导师评分的分层 prompt |
| GET/POST | `/memory/*` | 记忆操作(增删查) |
| GET | `/memory/user-weakness` | 用户弱点画像(Layer 1) |
| GET | `/dialog/difficulty-recommendation` | 难度推荐(Layer 3) |

### 7.2 与联调文档(《微信小程序接口联调说明》)的字段映射

**算法内部用 snake_case,接口层 `presenter` 转为 camelCase**:

| 联调字段 | 算法内字段 | 谁负责 |
|---|---|---|
| `sessionId` | `session.session_id` | 算法 |
| `taskId` | `session.task_id`(透传) | 算法 |
| `round` / `totalRounds` | `session.round` / 动态有效轮次 | 算法 |
| `score` | `score_result.total_score` | 算法 |
| `dimensionScores` | `score_result.dimension_scores` 转换 | 算法 |
| `weakTags` | `score_result.weakness_tags` | 算法 |
| `suggestion` | `score_result.suggestion` | 算法 |
| `source` | 根据 `score.method` 动态决定 LLM_BASED/RULE_BASED | 算法 |
| `resultId` | `longterm_memory.memory_id` | 算法(mock) |
| `scoreDelta` | 固定 0 | **Java 后端需替换** |
| `rewardPoints` / `rewardExp` | mock 公式 | **Java 后端需替换** |
| `certificationTitle/Desc` | 按最高维度选模板 | **Java 后端需替换** |

详见 [docs/backend_integration_guide.md](backend_integration_guide.md)。

### 7.3 `source` 字段语义

| 值 | 含义 | 什么情况返回 |
|---|---|---|
| `LLM_BASED` | LLM 真实评分了 | DeepSeek 调用成功 |
| `RULE_BASED` | 规则评分兜底 | 无 KEY / LLM 调用失败 / Pydantic 校验失败 / `AI_COACH_SCORER=rule` |

Java 后端可根据这个字段判断"是否走了 LLM 链路"。

---

## 8. 配置(环境变量)

```powershell
# Embedding
$env:AI_COACH_EMBEDDING_BACKEND="sentence_transformers"     # 默认
$env:AI_COACH_EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"      # 默认中文

# 记忆
$env:AI_COACH_REDIS_URL="redis://localhost:6379/0"          # 短期
$env:AI_COACH_POSTGRES_DSN="postgresql://..."               # 长期
$env:AI_COACH_SHORT_MEMORY_BACKEND="auto"                   # auto/json/redis
$env:AI_COACH_LONG_MEMORY_BACKEND="auto"                    # auto/json/postgres

# LLM 评分 + LLM 客户(DeepSeek)
$env:DEEPSEEK_API_KEY="sk-xxx"                              # 必需,不设回退规则
$env:AI_COACH_SCORER="llm"                                  # llm / rule
$env:AI_COACH_CUSTOMER_LLM="llm"                            # llm / template
$env:AI_COACH_LLM_MODEL="deepseek-chat"                     # 模型名
$env:AI_COACH_LLM_TIMEOUT="20"                              # 超时(秒)

# BERT-mini(当前禁用)
$env:AI_COACH_BERT_MINI_FUSION="0"                          # 0 / 1
```

**所有 env 都有合理默认值,不配也能跑 demo**(各组件自动降级)。

### 8.1 Docker 开发环境

开发联调推荐直接使用 Docker Compose，一次性拉起算法服务、Redis 和 PostgreSQL：

```powershell
cd ai-coach-algorithm
docker compose up -d --build
```

启动后访问：

```text
http://127.0.0.1:8000/docs
```

健康检查：

```powershell
curl http://127.0.0.1:8000/health
```

健康状态里应看到：

```json
{
  "memory": {
    "short_term_memory": {"active_backend": "redis", "available": true},
    "long_term_memory": {"active_backend": "postgresql", "available": true}
  }
}
```

Compose 内部固定使用容器服务名连接依赖：

```text
AI_COACH_REDIS_URL=redis://redis:6379/0
AI_COACH_POSTGRES_DSN=postgresql://ai_coach:ai_coach_dev@postgres:5432/ai_coach
```

为了降低新同事首次启动成本，Docker 开发环境默认使用 `hash` embedding，不下载 BGE 模型。需要验证真实中文 embedding 时设置：

```powershell
$env:AI_COACH_DOCKER_EMBEDDING_BACKEND="sentence_transformers"
$env:AI_COACH_DOCKER_EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"
docker compose up -d --build
```

常用命令：

```powershell
docker compose up -d          # 启动
docker compose up -d --build  # Dockerfile/依赖变更后重建
docker compose logs -f        # 看日志
docker compose down           # 停止,保留 Redis/PostgreSQL 数据
docker compose down -v        # 停止并清空本地数据库卷
```

---

## 9. 可观测性

### 9.1 结构化日志(`ai_coach.llm` logger)

每次 LLM 调用输出一行结构化日志(经 stdlib `logging` extra 字段):

```python
logger.info("llm_call", extra={
    "llm_method": "finish",            # finish / reply / customer / finish_schemafix
    "llm_scene_id": "INS_PERIODIC",
    "llm_model": "deepseek-chat",
    "llm_input_tokens": 1520,
    "llm_output_tokens": 312,
    "llm_cached_tokens": 1240,         # ← DeepSeek prefix cache 命中数
    "llm_cache_hit_rate": 0.8158,
    "llm_latency_ms": 1843,
    "llm_success": True,
    "llm_error_type": None,
    "llm_retry_count": 0,              # rate limit 重试次数
    "llm_rate_limited": False,
})
```

接 ELK / Loki / CloudWatch 直接按 JSON 字段查询。

### 9.2 /metrics/llm 接口

返回进程级聚合数据(按 method × scene 分桶):

```json
{
  "totals": {
    "call_count": 12,
    "input_tokens": 18500,
    "output_tokens": 3600,
    "cached_tokens": 14200,
    "cache_hit_rate": 0.7676
  },
  "by_bucket": [
    {
      "method": "finish",
      "scene_id": "INS_PERIODIC",
      "call_count": 1,
      "success_count": 1,
      "success_rate": 1.0,
      "rate_limited_count": 0,
      "input_tokens": 1830,
      "output_tokens": 412,
      "cached_tokens": 1450,
      "cache_hit_rate": 0.7923,
      "avg_latency_ms": 2104,
      "errors": {}
    }
  ]
}
```

**关键指标看什么:**

| 指标 | 健康范围 | 异常含义 |
|---|---|---|
| `success_rate` | > 0.95 | LLM 频繁失败,检查 KEY/网络/prompt |
| `cache_hit_rate` | > 0.6 | 静态层稳定,prefix cache 工作正常 |
| `cache_hit_rate ≈ 0` | — | 静态层有不稳定 byte(时间戳/UUID),需排查 |
| `rate_limited_count` 持续增长 | — | 触发 DeepSeek 限流,需升级套餐或降并发 |
| `avg_latency_ms` > 5000 | — | 网络问题或 prompt 太长 |

### 9.3 Rate limit 重试日志

```
INFO  llm_json/finish retry 1/2 after RateLimitError (waiting 1.13s)
INFO  llm_json/finish retry 2/2 after RateLimitError (waiting 2.05s)
```

3 次都失败才放弃,该次调用 `rate_limited_count += 1` 并最终 fallback 到 rule_scorer。

---

## 10. 失败回退矩阵

每个 LLM 链路点失败时的兜底行为:

| 失败点 | 兜底 | 用户感知 |
|---|---|---|
| 无 `DEEPSEEK_API_KEY` | 评分走 rule_scorer / 客户走模板 | source=RULE_BASED,行为退化但可用 |
| LLM 网络超时 / 5xx | 自动重试 3 次,失败后兜底 | 延迟稍长,最终 source=RULE_BASED |
| LLM 429 限流 | 退避重试 3 次 | 同上 + metrics 标记 rate_limited |
| LLM 返回非 JSON | json-repair 修复 / 代码块提取 | 透明,90%+ 能救活 |
| Pydantic 校验失败(矛盾/超范围) | 重试一次让 LLM 自修 | 透明,70%+ 能修对 |
| Pydantic 重试也失败 | 兜底 rule_scorer | source=RULE_BASED |
| 客户追问 LLM 失败 | 模板查表 `CUSTOMER_INTENT_PROBES` | 追问句变成固定模板 |
| Redis/PG 不可用 | JSON 文件兜底 | 透明 |
| Chroma 向量库异常 | 关键词 lexical fallback | 检索质量下降但不报错 |
| 整个 LLM 子系统挂 | 系统**仍能工作**,全部走规则路径 | source=RULE_BASED,质量降级 |

**核心承诺:任何依赖失败,系统不报 500,降级运行。**

---

## 11. 数据模型

### 11.1 客户画像(`data/customer_profiles.json`)

```json
{
  "customer_id": "CUST_LIQUIDITY_PERIODIC",
  "customer_type": "流动性担忧型",
  "scene_id": "INS_PERIODIC",
  "personality": "谨慎,担心钱被长期锁定...",
  "concern": "缴费期限太长、每年续缴压力...",
  "expected_intents": ["liquidity_concern", "procedure_question"],
  "opening_question": "这个要每年交、交那么多年,万一...",
  "difficulty_level": "中"
}
```

39 个画像,覆盖全部 14 个场景,每场景 2-3 个难度等级(低/中/高):

| 场景 | scene_id | 低 | 中 | 高 |
|---|---|---|---|---|
| 分红险异议处理 | INS_DIVIDEND | 收益好奇型 | 收益敏感型 | 专业质疑型 |
| 期交保险营销 | INS_PERIODIC | 好奇了解型 | 流动性担忧型 | 强势质疑型 |
| 保险综合营销 | INS_GENERAL | 礼貌推脱型 | 拒绝犹豫型 | 反感抵触型 |
| 基金异议处理 | FUND_OBJECTION | 基金新手型 | 风险厌恶型 | 激进追责型 |
| ... | ... | ... | ... | ... |

完整列表见 [algorithms/06_memory_and_adaptive.md §6](algorithms/06_memory_and_adaptive.md)。

`start_dialogue` 支持自适应难度选择:用户连续高分自动升难度,连续低分自动降。

### 11.2 评分标准(`data/marketing_scoring_criteria.json`)

每条 rubric 含:

```json
{
  "criterion_id": "MSC_INS_INS_PERIODIC_OBJECTION_HANDLING",
  "scene_id": "INS_PERIODIC",
  "knowledge_type": "objection_handling",
  "answer_goal": "回应客户异议,基于产品事实进行解释...",
  "must_points": [
    "说明期交保险的缴费期限和持续缴费要求",
    "区分保障责任和收益演示",
    "..."
  ],
  "compliance_red_lines": ["保证收益", "稳赚", "保本", ...],
  "key_terms": ["现金价值", "保障责任", ...]
}
```

31 条 criterion,按 `(scene_id, knowledge_type)` 唯一,`get_primary_criterion(scene_id)` 按优先级查表(`objection_handling > product_intro > sales_process > raw_script > phone_invitation > compliance_note`)。

### 11.3 标注集

| 文件 | 用途 |
|---|---|
| `data/intent_eval_candidates.jsonl` | 178 条候选(自动采样) |
| `data/intent_eval_gold.jsonl` | 193 条人工标 gold |
| `data/intent_train.jsonl` | 70% 训练切分(自动) |
| `data/intent_eval.jsonl` | 30% 验证切分 |

详见 [intent_annotation_schema.md](intent_annotation_schema.md)。

---

## 12. 试用流程

详见 [README.md](../README.md) 试用流程章节。简要:

```powershell
# 1. 推荐启动方式: Docker 开发环境
docker compose up -d

# 可选:配置 DeepSeek key 后重启,启用 LLM 评分 + LLM 客户模拟
$env:DEEPSEEK_API_KEY = "你的key"
docker compose up -d

# 本机直跑也可用:
# .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# 2. 打开 http://127.0.0.1:8000/docs

# 3. 顺序调用:
#    POST /dialog/start    → 拿 sessionId
#    POST /dialog/reply (×N)
#    POST /dialog/finish
#    GET  /metrics/llm     → 看 token / cache hit
```

演示亮点:
- **对话中故意踩合规雷** → AI 客户当场尖锐反击,把违规具体化逼问
- **后续轮次挽救** → AI 客户语气缓和,推进办理意向
- **finish** → 4 维度评分 + 合规红线一票否决 + LLM 自然语言 suggestion
- **/metrics/llm** → 演示 cache_hit_rate > 70%,token 成本省了 60%+(reply 不再评分进一步降低消耗)

---

## 13. 已知技术债 / 未来计划

### 已完成

- ✅ Async + 并行 LLM 调用(reply 延迟砍半)
- ✅ 3 层 JSON 解析兜底(json → json-repair → Pydantic)
- ✅ Pydantic 内部一致性校验(防"合规度 100 + 含合规风险标签"幻觉)
- ✅ 5 层 prompt 架构(prefix cache 友好)
- ✅ 静态层进程级缓存
- ✅ Rate limit 退避重试
- ✅ 结构化日志 + /metrics/llm 接口
- ✅ Layer 1 — 弱点画像聚合,注入 Customer/Scorer prompt L2
- ✅ Layer 2 — ChromaDB 向量化记忆,语义检索替代关键词匹配
- ✅ Layer 3 — 自适应难度推荐,自动升降客户画像难度
- ✅ 客户画像从 4 个扩展到 39 个,覆盖全部 14 个场景 × 2-3 难度
- ✅ Docker 开发环境:算法服务 + Redis + PostgreSQL 一键启动

### 待办

| 优先级 | 项 | 说明 |
|---|---|---|
| P1 | 回归测试集 | 攒 30 条 gold 对话,每次 prompt 改完跑一遍看不回归 |
| P1 | 多场景压测 | 14 个 scene 全覆盖验证(重点验证新增场景的画像质量) |
| P2 | Cost 看板 | metrics 接到真实监控系统(不在内存里) |
| P2 | LLM 评分集校验 | 攒 gold 评分集对 LLM 评分做精度评估 |
| P2 | 生产容器化加固 | 镜像版本锁定、secret 管理、资源限制、日志采集、非 reload 启动 |
| P3 | BERT-mini 训练优化 | 当前禁用,若要启用需:补样本到 300+ / save best epoch / 降学习率 |
| P3 | LLM 评分多模型对比 | 接入 Claude / GPT 做 ensemble 提高鲁棒性 |
| P3 | trace_id 端到端透传 | Java→算法→DeepSeek 串起来,日志可串 |

### 设计上的取舍(知道但不打算改)

| 决策 | 原因 |
|---|---|
| Metrics 只在内存 | dev/demo 用,生产应该接真实监控,不要靠 in-process 持久化 |
| 业务字段 mock(rewardPoints 等) | 不是算法职责,等 Java 后端就位 |
| BERT-mini 暂时关闭 | LLM 客户已经接管追问生成,gap 检测的语义压力下降,BERT 优先级降低 |
| 保留 JSON 兜底 | Docker 开发环境已接 Redis/PostgreSQL；无依赖或故障时仍可退回 JSON,保证 demo 可跑 |

---

## 14. 联系人

- 算法负责:xinanQ
- 个人仓库:https://github.com/XinanQ/ai-coach-algorithm
- 团队合并入口:`feature/ai-coach-algorithm` 分支(在 `kw-Jak/financial-performance-team` 仓库,作为 `ai-coach-algorithm/` 子目录)
