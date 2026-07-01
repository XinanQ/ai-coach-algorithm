# 算法文档 06 — 记忆系统与自适应难度

> 涉及代码:
> - 弱点画像:[app/core/weakness_profile.py](../../app/core/weakness_profile.py)
> - 向量记忆:[app/core/memory_vector_store.py](../../app/core/memory_vector_store.py)
> - 自适应难度:[app/core/adaptive_difficulty.py](../../app/core/adaptive_difficulty.py)
> - 记忆管理:[app/core/memory_manager.py](../../app/core/memory_manager.py) + [memory_store.py](../../app/core/memory_store.py)
> - Prompt 注入:[app/core/llm/prompts/customer.py](../../app/core/llm/prompts/customer.py) + [scorer.py](../../app/core/llm/prompts/scorer.py)
> - 对话编排:[app/core/dialog_manager.py](../../app/core/dialog_manager.py)

## 1. 核心问题

原始系统每次训练独立运行,不记住用户的历史表现。带来三个问题:

| 问题 | 影响 |
|---|---|
| **不知道用户弱在哪** | AI 客户每次问的问题与用户水平无关,高手和新手面对同样的压力 |
| **检索不精准** | 用关键词匹配查历史记录,语义相近但用词不同的训练记忆找不到 |
| **难度无法适应** | 用户连续高分仍然面对同样难度,没有挑战性;连续低分也不降难度 |

**解法:三层升级**
- **Layer 1** — 弱点画像聚合(WeaknessProfile),注入 Prompt
- **Layer 2** — 向量化记忆检索(ChromaDB),替代关键词匹配
- **Layer 3** — 自适应难度推荐(AdaptiveDifficulty),自动选择客户画像

## 2. 三层记忆架构

```
                    ┌─────────────────────────────┐
                    │       Layer 3: 自适应难度     │
                    │  recommend_difficulty()       │
                    │  连续≥85→升 / 连续<60→降       │
                    └──────────────┬──────────────┘
                                   │ 读取历史成绩
                    ┌──────────────▼──────────────┐
                    │       Layer 1: 弱点画像       │
                    │  build_weakness_profile()     │
                    │  维度均值 + 趋势 + 高频弱项    │
                    └──────────────┬──────────────┘
                                   │ 聚合
         ┌─────────────────────────▼──────────────────────────┐
         │                  长期记忆存储                         │
         │                                                      │
         │  ┌─────────────┐    ┌───────────────────────┐       │
         │  │  主存储       │    │  Layer 2: 向量索引     │       │
         │  │  PG / JSON   │◄──►│  ChromaDB + bge-zh    │       │
         │  │  (全量记录)   │    │  (语义检索 embedding) │       │
         │  └─────────────┘    └───────────────────────┘       │
         └─────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────▼──────────────────────────┐
         │                  短期记忆(Session)                   │
         │               Redis / JSON                           │
         │        当前对话状态 + weakness_prompt 快照             │
         └─────────────────────────────────────────────────────┘
```

### 2.1 短期记忆(Session State)

| 项 | 说明 |
|---|---|
| 存储位置 | Redis(生产) / `mock_db/mock_dialog_sessions.json`(开发) |
| 生命周期 | 单次对话,Redis TTL 24 小时 |
| 数据隔离 | 按 `session_id` 隔离 |
| 存储内容 | messages、weakness_profile 快照、场景配置、客户画像、difficulty_level |
| 作用 | 让 AI 在一次对话中保持上下文连贯 |

### 2.2 长期记忆(Training Records)

| 项 | 说明 |
|---|---|
| 存储位置 | PostgreSQL(生产) / `mock_db/longterm_memory.json`(开发) |
| 数据隔离 | 按 `user_id` + `scenario_id` 过滤查询 |
| 存储内容 | score、weakness_tags、summary、feedback、score_result、messages |
| 作用 | 记录训练历史,供 Layer 1 弱点画像聚合、Layer 3 难度推荐 |

### 2.3 向量索引(Semantic Search — Layer 2)

| 项 | 说明 |
|---|---|
| 存储位置 | ChromaDB(本地持久化),collection 名 `memory_longterm_<模型hash>` |
| Embedding 模型 | BAAI/bge-small-zh-v1.5(sentence_transformers),hash 兜底 |
| 数据隔离 | metadata 中存 `user_id` + `scenario_id`,查询时 `$and` 过滤 |
| 存储内容 | 每条长期记忆的 embedding(summary + feedback + weakness_tags + suggestion 拼接) |
| 作用 | 语义相似度检索历史训练记录(替代 lexical_similarity 关键词匹配) |

**向量索引的优势(实测):**

| 查询 | 期望匹配 | 关键词匹配 | 向量匹配(bge-zh) |
|---|---|---|---|
| "承诺收益保证回报" | "稳赚不赔"相关记录 | 匹配差(无共同关键词) | score=0.69,排名第一 |
| "客户情绪安抚" | "共情不足"相关记录 | 匹配差 | score=0.74,排名第一 |
| "提前取钱退保损失" | "流动性"相关记录 | 部分匹配 | score=0.73,排名第一 |

## 3. Layer 1 — 弱点画像(`weakness_profile.py`)

### 3.1 聚合逻辑

`build_weakness_profile(user_id, scene_id, limit=10)`:

```
查询 longterm_memory(按 user_id + scene_id,最近 10 次)
   ↓
遍历每条记录:
   - 收集 score → total_scores[]
   - 收集 weakness_tags → all_tags[]
   - 收集 dimension_scores → dim_scores{key: [score,...]}
   ↓
聚合:
   - avg_score = mean(total_scores)
   - dimension_averages = {key: mean(scores)}
   - dimension_trends = {key: _compute_trend(scores)}  ← 前半 vs 后半均值,差≥5
   - frequent_weakness_tags = 出现≥2次的标签(top 5)
   - recent_weakness_tags = 最近一次的弱项
   - recent_suggestion = 最近一次的评分建议
```

### 3.2 趋势计算(`_compute_trend`)

| 条件 | 趋势 |
|---|---|
| 后半段均值 − 前半段均值 ≥ 5 | 上升 |
| 后半段均值 − 前半段均值 ≤ −5 | 下降 |
| 差值在 (−5, 5) 内 | 持平 |

### 3.3 Prompt 注入

`WeaknessProfile.to_prompt_text(role)` 生成自然语言段落,注入 L2 动态层:

**客户视角**(role="customer"):
```
## 历史训练画像（该员工已练习 5 次，平均分 68）
- 反复出现的弱项：合规红线、共情不足
- **你应在对话中重点围绕这些弱项施压**，用更尖锐的追问测试员工是否改善
- 上一次训练的弱项：流动性说明不足
- 正在退步的维度：共情力（可加重追问力度）
```

**评分器视角**(role="scorer"):
```
## 历史训练画像（该员工已练习 5 次，平均分 68）
- 反复出现的弱项：合规红线、共情不足
- 评分时**重点关注这些弱项是否有改善**，如果改善了请在 suggestion 中肯定进步
- 各维度历史表现：
  合规度: 平均 72 分（持平）
  共情力: 平均 55 分（下降）
- 上次评分建议：补充退保条件说明
```

### 3.4 注入位置

```
CustomerContextLayer.render()
   └─ context["weakness_prompt"] → 追加到 L2 末尾

FinishContextLayer.render() / ReplyContextLayer.render()
   └─ context["weakness_prompt"] → 追加到 L2 末尾
```

新用户(无历史记录):`WeaknessProfile.has_history() == False`,不注入任何内容,行为与升级前一致。

## 4. Layer 2 — 向量化记忆检索(`memory_vector_store.py`)

### 4.1 写入流程

```
finish_dialogue → save_longterm(record)
   ↓
HybridLongTermMemoryStore.append(record)
   ├─ primary.append(record)         ← 写入 PG/JSON 主存储
   └─ self._vector_store.upsert(record)  ← 同步写入 ChromaDB
         ├─ _memory_text(record) → 拼接文本
         ├─ adapter.embed_query(text) → 生成 embedding
         └─ collection.upsert(ids, embeddings, metadatas)
```

**写入失败静默降级**:ChromaDB upsert 失败不影响主存储,只记 warning 日志。

### 4.2 检索流程

```
retrieve_history(query, user_id, scenario_id)
   ↓
HybridLongTermMemoryStore.retrieve()
   ├─ 优先: vector_store.query(query_text, user_id, scenario_id)
   │     ├─ embed_query(query_text) → 查询向量
   │     ├─ collection.query(where={user_id, scenario_id})
   │     ├─ 返回 [{memory_id, retrieval_score, distance}, ...]
   │     └─ 从主存储查完整记录,合并 retrieval_score
   │
   └─ 兜底: primary.retrieve() → lexical_similarity 关键词匹配
```

### 4.3 Collection 命名

按 embedding 模型签名生成:

```python
sig = f"{adapter.active_backend}:{adapter.active_model}:{adapter.dimensions}"
name = f"memory_longterm_{sha1(sig)[:12]}"
```

换模型自动新建 collection,不污染旧索引。

## 5. Layer 3 — 自适应难度(`adaptive_difficulty.py`)

### 5.1 推荐逻辑

`recommend_difficulty(user_id, scene_id, current_difficulty)`:

```
查询 longterm_memory(按 user_id + scene_id)
   ↓
取最近 N 次 score:
   - 连续 3 次 ≥ 85 → 推荐升一级(低→中, 中→高)
   - 连续 2 次 < 60 → 推荐降一级(高→中, 中→低)
   - 其他 → 维持当前难度
   ↓
分析弱势维度:
   - 最近 3 次某维度均分 < 60 → 标记为 weak_dimension
   ↓
生成训练建议:
   - 有弱势维度 → "建议专项加强：合规度、共情力"
   - 降级 → "建议先用低难度客户巩固基础话术"
   - 已达最高且要升 → "建议尝试不同场景拓展能力边界"
```

### 5.2 难度等级

| 等级 | 客户特征 | 适合谁 |
|---|---|---|
| **低** | 友善、愿意听解释、问题简单 | 新手或连续低分用户 |
| **中** | 有具体顾虑、需要认真应对 | 默认难度 |
| **高** | 情绪化、试探合规底线、连环追问 | 连续高分或需要挑战的老手 |

### 5.3 与 start_dialogue 的集成

```
start_dialogue(user_id, scene_id, difficulty=None, auto_difficulty=True)
   ↓
如果 difficulty 未指定 且 auto_difficulty=True:
   recommend_difficulty(user_id, scene_id) → rec
   difficulty = rec.recommended_difficulty
   ↓
get_customer_profile(scene_id, difficulty=difficulty)
   → 选择对应难度的客户画像
   ↓
返回结果中附带 difficulty_recommendation:
   {
     "recommended_difficulty": "高",
     "reason": "最近 3 次得分均 ≥85，建议提升难度",
     "recent_scores": [90, 88, 92],
     "weak_dimensions": [],
     "training_suggestion": ""
   }
```

前端可展示推荐理由,也可让用户手动覆盖难度选择。

## 6. 客户画像覆盖

升级后共 **39 个客户画像**,覆盖全部 **14 个场景**:

| 场景 | scene_id | 低 | 中 | 高 |
|---|---|---|---|---|
| 分红险异议处理 | INS_DIVIDEND | 收益好奇型 | 收益敏感型 | 专业质疑型 |
| 期交保险营销 | INS_PERIODIC | 好奇了解型 | 流动性担忧型 | 强势质疑型 |
| 保险综合营销 | INS_GENERAL | 礼貌推脱型 | 拒绝犹豫型 | 反感抵触型 |
| 保险电话邀约 | INS_INVITE | 友好接听型 | 忙碌推脱型 | 投诉警告型 |
| 保险异议处理 | INS_OBJECTION | 疑虑询问型 | 比较型客户 | 理赔纠纷型 |
| 保险办理流程 | INS_PROCESS | 流程咨询型 | 犹豫期关注型 | 代签纠纷型 |
| 基金定投营销 | FUND_FIXED_INVEST | 定投入门型 | 收益对比型 | 亏损质疑型 |
| 基金综合营销 | FUND_GENERAL | 理财转化型 | 产品选择型 | 套利试探型 |
| 基金电话邀约 | FUND_INVITE | 配合了解型 | 警惕筛选型 | 强势拒绝型 |
| 基金异议处理 | FUND_OBJECTION | 基金新手型 | 风险厌恶型 | 激进追责型 |
| 基金销售关键点 | FUND_SALE | 初次咨询型 | 比较犹豫型 | — |
| 财富管理资产配置 | WM_ASSET | 理财升级型 | 风险平衡型 | 高净值挑剔型 |
| 财富管理综合 | WM_GENERAL | 存款客户型 | 服务体验型 | — |
| 财富管理产品 | WM_PRODUCT | 产品了解型 | 到期转化型 | — |

每个画像包含:personality(性格)、concern(核心顾虑)、expected_intents(测试意图)、opening_question(开场白)、followup_strategy(追问策略)、difficulty_level(难度等级)。

## 7. 完整数据流

### 7.1 用户完成训练

```
finish_dialogue → score_result
   ├─ 写 longterm_memory(PG/JSON)        ← 主存储
   ├─ 同步写 ChromaDB embedding           ← 向量索引
   └─ 清理 session                        ← 短期记忆释放
```

### 7.2 用户开始新训练

```
start_dialogue(user_id, scene_id)
   ├─ recommend_difficulty() → 推荐难度     ← Layer 3
   ├─ get_customer_profile(difficulty=推荐)  ← 选画像
   ├─ build_weakness_profile() → 弱点画像   ← Layer 1
   │     └─ 查询 longterm_memory(最近 10 次)
   │     └─ 聚合维度均值、趋势、高频弱项
   ├─ 生成 weakness_prompt → 注入 session   ← Prompt 注入
   └─ 创建新 session(短期记忆)
```

### 7.3 训练中每轮回复

```
reply_dialogue(session_id, employee_message)
   ├─ 从 session 读取 weakness_prompt       ← Layer 1 信号
   ├─ retrieve_history(向量语义搜索)         ← Layer 2 检索
   └─ 传递 customer_weakness_prompt 给:
        └─ _next_customer_question() → AI 客户针对弱项施压
   （注:reply 评分已下线,弱点画像只在 finish 评分时通过 scorer_prompt 注入）
```

## 8. API 接口

### 8.1 GET /dialog/difficulty-recommendation

```
GET /dialog/difficulty-recommendation?user_id=U001&scene_id=INS_PERIODIC&current_difficulty=中
```

**Response:**
```json
{
  "user_id": "U001",
  "scene_id": "INS_PERIODIC",
  "current_difficulty": "中",
  "recommended_difficulty": "高",
  "reason": "最近 3 次得分均 ≥85，建议提升难度",
  "session_count": 5,
  "recent_scores": [88, 90, 92],
  "weak_dimensions": [],
  "training_suggestion": ""
}
```

### 8.2 GET /memory/user-weakness

```
GET /memory/user-weakness?user_id=U001&scene_id=INS_PERIODIC
```

**Response:**
```json
{
  "has_history": true,
  "profile": {
    "user_id": "U001",
    "session_count": 5,
    "avg_score": 72.4,
    "dimension_averages": {"合规度": 85.0, "共情力": 55.0},
    "dimension_trends": {"合规度": "上升", "共情力": "下降"},
    "frequent_weakness_tags": ["共情不足", "流动性说明不足"],
    "recent_weakness_tags": ["共情不足"],
    "recent_score": 78,
    "recent_suggestion": "加强对客户顾虑的共情回应"
  },
  "customer_prompt_preview": "## 历史训练画像...",
  "scorer_prompt_preview": "## 历史训练画像..."
}
```

## 9. 用户数据隔离

所有查询都带 `user_id` 过滤条件:

| 操作 | 过滤字段 |
|---|---|
| 查询长期记忆 | `WHERE user_id = ? AND scenario_id = ?` |
| 向量检索 | ChromaDB `where: {user_id: {$eq: ?}}` |
| 弱点画像聚合 | `list_longterm(user_id=?, scenario_id=?)` |
| 难度推荐 | `list_longterm(user_id=?, scenario_id=?)` |

用户 A 永远看不到用户 B 的训练记录。

## 10. 失败回退

| 失败点 | 兜底 | 影响 |
|---|---|---|
| ChromaDB 初始化失败 | `_vector_store = None`,走 lexical 关键词匹配 | 检索质量下降 |
| ChromaDB upsert 失败 | 静默跳过,主存储不受影响 | 新记录暂未索引 |
| ChromaDB query 失败 | 回退 `primary.retrieve()`(关键词) | 同上 |
| Embedding 模型加载失败 | hash embedding 兜底(128 维随机投影) | 语义检索退化为伪随机匹配 |
| 弱点画像查询失败 | 空 `WeaknessProfile`,不注入 prompt | 行为与新用户一致 |
| 难度推荐失败 | 返回默认"中"难度 | 不影响训练 |

**核心承诺:记忆层任何组件失败,系统不报 500,降级运行。**

## 11. 调优入口

| 想改什么 | 改哪里 |
|---|---|
| 升难度阈值(默认 ≥85) | `adaptive_difficulty.UPGRADE_THRESHOLD` |
| 升难度连续次数(默认 3) | `adaptive_difficulty.UPGRADE_STREAK` |
| 降难度阈值(默认 <60) | `adaptive_difficulty.DOWNGRADE_THRESHOLD` |
| 降难度连续次数(默认 2) | `adaptive_difficulty.DOWNGRADE_STREAK` |
| 弱点画像聚合范围(默认 10 次) | `weakness_profile.build_weakness_profile(limit=)` |
| 趋势判定差值(默认 ≥5) | `weakness_profile._compute_trend` |
| 高频标签阈值(默认 ≥2 次) | `weakness_profile.build_weakness_profile` 中 `count >= 2` |
| 客户画像内容 | `data/customer_profiles.json` |
| 弱点 prompt 措辞 | `weakness_profile.WeaknessProfile.to_prompt_text` |
| 向量检索条数(默认 5) | `memory_store.HybridLongTermMemoryStore.retrieve(limit=)` |
