# 算法服务对接说明（给 Java 后端）

本文档面向负责小程序后端的 Java 同事。AI 陪练算法服务是一个独立的 Python FastAPI 服务，负责陪练对话的 AI 客户提问、员工回答评分。Java 后端在收到小程序请求后，调用本服务获取算法结果，再补齐业务字段（积分、认证、scoreDelta）返回小程序。

## 1. 整体架构

```text
小程序
   │  /api/mini/practice/dialog/*  (X-Auth-Token 鉴权)
   ▼
Java 后端
   │  鉴权、taskId→scene_id 映射、积分/认证/历史分数
   │  HTTP 调用 ▼
Python 算法服务（本仓库）
   │  /dialog/start  /dialog/reply  /dialog/finish
```

**职责边界：**

| 算法服务负责 | Java 后端负责 |
|---|---|
| AI 客户问题生成（gap 驱动） | 用户鉴权、token 解析 |
| 员工回答的 4 维度评分 | `taskId` ↔ `scene_id` 映射 |
| 漏答要点检测、合规红线检测 | `scoreDelta`（查历史分数对比） |
| 自然语言改进建议（suggestion） | `rewardPoints` / `rewardExp`（积分规则） |
| 对话轮次控制（round / finished） | `certificationTitle` / `certificationDesc`（认证规则） |
| 长期记忆（session/longterm，可改 PG） | 任务/模板/排行榜的业务 CRUD |

算法服务**不接触用户态**（无 token、无用户表、无积分库），Java 后端是唯一的小程序入口。

## 2. 部署与连接信息

| 项 | 值 |
|---|---|
| 服务类型 | Python FastAPI |
| 推荐开发启动 | `docker compose up -d --build` |
| 本机直跑启动 | `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| 健康检查 | `GET /health` |
| OpenAPI 文档 | `GET /docs` (浏览器打开) |
| 本地联调 URL | `http://127.0.0.1:8000` |
| 内网 URL（待定） | 例：`http://ai-coach-algo:8000` |
| 鉴权方式 | **暂无**，仅限内网调用；如需鉴权需另加 |

推荐启动示例（算法服务 + Redis + PostgreSQL）：
```powershell
cd ai-coach-algorithm
docker compose up -d --build
```

验证：
```powershell
curl http://127.0.0.1:8000/health
```

期望 `memory.short_term_memory.active_backend=redis`，`memory.long_term_memory.active_backend=postgresql`。这表示短期 session 已接入 Redis，长期训练记忆已接入 PostgreSQL，不是 JSON fallback。

本机直跑示例（不使用 Docker 时）：
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Docker Compose 当前定位为**开发/联调环境**，已覆盖算法服务本体、Redis、PostgreSQL 和健康检查。生产部署仍需另行补充服务鉴权、密钥管理、资源限制、日志采集和真实内网域名。

## 2.1 任务首页/场景目录接口（可选）

如果小程序任务页需要先做成“训练方向 + 推荐场景卡片”的样式，Java 后端可以临时调用算法侧任务目录接口，再补齐真实业务字段：

```text
GET /practice/tasks
GET /practice/tasks?direction=objection
GET /practice/tasks/{taskId}
GET /practice/tasks/{taskId}/scripts
GET /practice/scripts/{scriptId}?taskId={taskId}
```

`/practice/tasks` 的响应已经按页面展示做了 camelCase 和中文标签适配：
- 默认从 39 个客户画像动态生成 39 个训练任务卡，并按 7 个训练方向分类

```json
{
  "levelName": "Lv5 专业进阶",
  "points": 1260,
  "target": 1800,
  "streakDays": 7,
  "weekGain": 320,
  "tabs": [
    { "key": "assigned", "label": "上级下发" },
    { "key": "self", "label": "自主任务" },
    { "key": "done", "label": "已完成" }
  ],
  "directions": [
    { "key": "customer_touch", "label": "客户触达" },
    { "key": "needs", "label": "需求识别" },
    { "key": "product", "label": "产品讲解" },
    { "key": "objection", "label": "异议处理" },
    { "key": "close", "label": "成交促成" },
    { "key": "compliance", "label": "合规风险" },
    { "key": "service", "label": "售后维护" }
  ],
  "selectedTab": "self",
  "selectedDirection": null,
  "total": 39,
  "returned": 39,
  "list": [
    {
      "taskId": "TASK_CUST_RATE_DIVIDEND_HIGH",
      "sceneId": "INS_DIVIDEND",
      "customerId": "CUST_RATE_DIVIDEND_HIGH",
      "category": "保险",
      "title": "分红险异议处理 · 专业质疑型",
      "tags": ["收益关注", "本金安全", "合规敏感", "高难度"],
      "intentTags": ["rate_concern", "safety_concern", "compliance_sensitive"],
      "intentLabels": ["收益关注", "本金安全", "合规敏感"],
      "durationText": "8分钟",
      "description": "分红演示和实际差距、现金价值过低、封闭期太长。"
    }
  ]
}
```

字段边界：

| 字段 | 建议来源 | 说明 |
|---|---|---|
| `sceneId` / `customerId` / `intentTags` / `intentLabels` | 算法 | 用于启动陪练和解释算法标签 |
| `title` / `category` / `tags` / `durationText` / `description` | 算法可先提供 | 页面展示字段，默认来自 39 个客户画像 |
| `points` / `target` / `streakDays` / `weekGain` | Java 后端最终覆盖 | 用户成长、积分、连续训练天数属于业务数据 |
| `tab` / `status` / `level` | Java 后端最终覆盖 | 上级下发、自主任务、完成状态属于任务业务流 |

标准话术资料卡片：

| 字段 | 来源 | 说明 |
|---|---|---|
| `scriptEntry` | `GET /practice/tasks/{taskId}` | 场景简介页“查看标准话术”按钮入口，含 `label` / `endpoint` / `count` |
| `scriptCards` | `GET /practice/tasks/{taskId}` | 任务详情内联返回的前 6 张话术卡片 |
| `GET /practice/tasks/{taskId}/scripts` | 算法 | 返回该任务对应的话术卡片列表 |
| `GET /practice/scripts/{scriptId}?taskId={taskId}` | 算法 | 返回单张话术详情，用于“话术详情 / 复制标准话术”页 |

话术卡片核心字段：`scriptId`、`title`、`subtitle`、`tags`、`standardSpeech`、`copyText`、`sourceFile`、`sourceChunkId`。前端展示文本用 `standardSpeech`，复制按钮用 `copyText`。

`GET /dialog/profiles` 也会保留原始 `expected_intents`，并额外返回 `tags` / `intentLabels` 中文展示字段。前端展示标签时优先用 `tags`，不要直接展示 `expected_intents`。

## 3. 三个核心接口

请求体均为 JSON，响应体均为 `application/json; charset=utf-8`。所有字段已对齐《微信小程序接口联调说明》的 camelCase 命名。

### 3.1 POST /dialog/start

**用途：** 开启一次陪练，返回 AI 客户的第一句开场白。

**Request:**
```json
{
  "user_id": "U_TEST",
  "scene_id": "INS_PERIODIC",
  "task_id": "t1",
  "total_rounds": 3,
  "customer_id": null,
  "difficulty": null,
  "auto_difficulty": true
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `user_id` | 是 | 算法侧用于写长期记忆的用户标识（Java 后端用真实 employeeId 传） |
| `scene_id` | 是 | 算法场景 id，见 §5 |
| `task_id` | 否 | 业务 taskId，原样回传给前端，算法不解释 |
| `total_rounds` | 否 | 总轮数，默认 3 |
| `customer_id` | 否 | 指定客户画像 id；不传则按 scene_id + difficulty 找匹配画像 |
| `difficulty` | 否 | 手动指定难度：`"低"` / `"中"` / `"高"`。不传则由算法自动推荐 |
| `auto_difficulty` | 否 | 是否自动推荐难度，默认 `true`。设为 `false` 时跳过推荐,使用默认"中" |

**Response:**
```json
{
  "sessionId": "S_a1b2c3d4e5f6",
  "taskId": "t1",
  "round": 1,
  "totalRounds": 3,
  "difficultyLevel": "高",
  "messages": [
    { "role": "ai", "content": "这个分红险，你能不能把历年的实际分红数据给我看一下？别拿演示利率忽悠我。" }
  ],
  "difficultyRecommendation": {
    "recommended_difficulty": "高",
    "reason": "最近 3 次得分均 ≥85，建议提升难度",
    "recent_scores": [88, 90, 92],
    "weak_dimensions": [],
    "training_suggestion": ""
  }
}
```

**新增字段说明:**
- `difficultyLevel`：本次训练实际使用的难度等级
- `difficultyRecommendation`：仅在自动推荐时出现,包含推荐理由和依据。前端可展示给用户

**Java 后端处理：** 字段可直接透传给小程序。新增字段为可选,前端不展示也不影响训练。

### 3.2 POST /dialog/reply

**用途：** 提交员工本轮回复，返回 AI 客户的追问。

> ⚠️ **接口变更（取消实时评分）**：reply 不再返回 `liveScore` 和 `source`。
> 每轮实时评分已下线——分数只在 `/dialog/finish` 结束时计算一次（基于完整对话）。
> 前端请移除对话过程中的实时分数展示，只在结算页显示最终评分。

**Request:**
```json
{
  "session_id": "S_a1b2c3d4e5f6",
  "employee_message": "我先了解您的资金安排，期交保险需要每年持续缴费，请以保险合同为准。"
}
```

**Response（中间轮）：**
```json
{
  "round": 2,
  "totalRounds": 3,
  "message": { "role": "ai", "content": "那我万一中途要用钱、或者交不上了，能取出来吗？会不会亏？" },
  "finished": false
}
```

**Response（末轮，即第 `totalRounds` 次 reply）：**
```json
{
  "round": 3,
  "totalRounds": 3,
  "message": null,
  "finished": true
}
```

**Java 后端处理：** 字段可直接透传。前端收到 `finished: true` 后会自动调 finish 接口。

### 3.3 POST /dialog/finish

**用途：** 结束陪练，返回 4 维度评分 + 改进建议。

**Request:**
```json
{ "session_id": "S_a1b2c3d4e5f6" }
```

**Response:**
```json
{
  "resultId": "MEM_639f01797e1d",
  "taskId": "INS_PERIODIC",
  "score": 77,
  "scoreDelta": 0,
  "certificationTitle": "新晋「合规揭示达人」",
  "certificationDesc": "合规度表现突出，完成专项认证",
  "rewardPoints": 77,
  "rewardExp": 154,
  "dimensionScores": [
    { "name": "合规度", "score": 100, "level": "优秀" },
    { "name": "异议处理", "score": 70, "level": "合格" },
    { "name": "逻辑结构", "score": 74, "level": "合格" },
    { "name": "共情力", "score": 57, "level": "待提升" }
  ],
  "weakTags": ["标准要点覆盖不足", "需求挖掘与共情不足"],
  "suggestion": "建议：补充以下标准要点：...；加强对客户顾虑的共情。",
  "source": "RULE_BASED"
}
```

**Java 后端处理：见 §4。**

## 4. 算法字段 vs 业务字段（Java 后端必读）

`/dialog/finish` 返回里，字段分两类：

### 4.1 算法字段（Java 直接透传）

| 字段 | 来源 | 说明 |
|---|---|---|
| `score` | 算法 | 4 维度加权总分（0-100） |
| `dimensionScores` | 算法 | 4 维度子分（合规度/异议处理/逻辑结构/共情力） |
| `weakTags` | 算法 | 弱点标签数组 |
| `suggestion` | 算法 | 自然语言改进建议 |
| `source` | 算法 | 评分方式：`RULE_BASED` = 规则评分；`LLM_BASED` = DeepSeek 评分。算法侧根据当前实际运行的 scorer 动态返回，无需 Java 关心 |

### 4.2 业务字段（Java 后端**必须覆盖**为真实值）

算法侧给的是 **mock 占位**，让前端能立刻联调，但生产必须由 Java 替换：

| 字段 | 算法 mock 规则 | Java 后端应替换为 |
|---|---|---|
| `resultId` | 算法长期记忆 id | 业务库的训练结果记录 id |
| `taskId` | 回退到 `scene_id` | 真实业务 taskId（从 request 上下文取） |
| `scoreDelta` | 固定 0 | 当前 score − 该用户上次同场景 score |
| `rewardPoints` | `max(10, total)` | 业务积分规则计算结果 |
| `rewardExp` | `rewardPoints × 2` | 业务经验规则计算结果 |
| `certificationTitle` / `certificationDesc` | 按最高分维度取的固定文案 | 业务认证规则（连续达标 N 次等） |

**实现建议：** Java 收到算法响应后，对这 6 个字段做覆盖，其余字段透传。

## 5. 场景与客户画像

算法目前支持 **14 个场景**（`scene_id`），共 **39 个客户画像**,每场景 2-3 个难度等级。数据在 [data/customer_profiles.json](../data/customer_profiles.json)：

| scene_id | 场景名称 | 难度等级 | 重点考察 |
|---|---|---|---|
| `INS_PERIODIC` | 期交保险营销 | 低/中/高 | 期限说明、提前退保、合同合规 |
| `INS_DIVIDEND` | 分红险异议处理 | 低/中/高 | 分红不确定性、保障 vs 收益 |
| `INS_GENERAL` | 保险综合营销 | 低/中/高 | 共情、不强推、灵活方案 |
| `INS_INVITE` | 保险电话邀约 | 低/中/高 | 开场话术、邀约成功率 |
| `INS_OBJECTION` | 保险异议处理 | 低/中/高 | 异议应对、比较分析 |
| `INS_PROCESS` | 保险办理流程 | 低/中/高 | 流程合规、犹豫期说明 |
| `FUND_FIXED_INVEST` | 基金定投营销 | 低/中/高 | 定投逻辑、长期持有 |
| `FUND_GENERAL` | 基金综合营销 | 低/中/高 | 产品匹配、风险评估 |
| `FUND_INVITE` | 基金电话邀约 | 低/中/高 | 开场切入、异议处理 |
| `FUND_OBJECTION` | 基金异议处理 | 低/中/高 | 净值波动、风险匹配 |
| `FUND_SALE` | 基金销售关键点 | 低/中 | 合规销售、适当性匹配 |
| `WM_ASSET` | 财富管理资产配置 | 低/中/高 | 资产分散、风险平衡 |
| `WM_GENERAL` | 财富管理综合 | 低/中 | 客户服务、需求挖掘 |
| `WM_PRODUCT` | 财富管理产品 | 低/中 | 产品介绍、到期转化 |

**自适应难度：** 算法根据用户历史成绩自动推荐难度等级(连续 3 次 ≥85 分升难度,连续 2 次 <60 分降难度)。也可通过 `difficulty` 参数手动指定。

**taskId → scene_id 映射由 Java 后端维护**（建议在任务表加 `scene_id` 字段）。

新增场景需要算法侧扩 `customer_profiles.json` 和 `marketing_scoring_criteria.json`，请提前沟通。

## 6. 错误码

| HTTP | 含义 | 触发 |
|---|---|---|
| 200 | 成功 | 正常返回 |
| 404 | session 不存在 | `session_id` 找不到（已过期或从未创建） |
| 422 | 参数校验失败 | 必填字段缺失或类型错误（FastAPI 自动） |
| 500 | 算法内部错误 | 检索失败、模型加载失败等 |

错误响应格式（FastAPI 默认）：
```json
{ "detail": "session not found: S_xxx" }
```

## 7. 联调

| 事项 | 负责方 | 状态 |
|---|---|---|
| 算法服务部署 URL | 运维 / Java | 待定 |
| taskId → scene_id 映射表落地 | Java | 待定 |
| 算法服务鉴权（如果需要） | 双方 | 暂无 |
| 长期记忆存储是否改 MySQL | 架构 | 开发环境已接 PostgreSQL；生产是否统一 MySQL 待定 |
| Docker 化 | 算法侧 | 已完成开发联调版：API + Redis + PostgreSQL |
| trace_id 透传日志 | 双方 | 待办 |

## 8. 算法演进对 Java 的影响

LLM 评分 + LLM 模拟客户（DeepSeek）已接入：

**评分（仅 finish 的最终分，reply 实时评分已下线）：**
- 为降低高并发下的 token 消耗，**每轮 reply 不再评分**——分数只在 finish 算一次（基于完整对话）
- 算法侧设置 `DEEPSEEK_API_KEY` 后自动启用，finish 的 `source` 从 `RULE_BASED` 变 `LLM_BASED`
- `score`、`dimensionScores`、`suggestion` 由 LLM 评委结合检索到的标准话术生成
- LLM 失败/超时自动回退规则评分，`source` 退回 `RULE_BASED`

**客户追问（reply 返回的 `message.content`）：**
- 设置 `DEEPSEEK_API_KEY` 后，AI 客户的下一句话由 LLM 根据画像 + 对话历史 + gap 分析 + RAG 检索结果生成
- 算法侧只负责"分析该追问什么"，LLM 负责"自然地把追问说出来"——避免模板重复、贴合上下文
- LLM 失败自动回退到 `CUSTOMER_INTENT_PROBES` 固定模板（行为与对接前一致）

**Java 后端无需任何改动**，接口形态完全不变。关键环境变量：

| 变量 | 默认 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | (必需) | 不设则评分走规则、客户追问走模板 |
| `AI_COACH_SCORER` | `llm` | `llm` / `rule` — 评分模式开关 |
| `AI_COACH_CUSTOMER_LLM` | `llm` | `llm` / `template` — 客户追问模式开关 |
| `AI_COACH_LLM_MODEL` | `deepseek-chat` | DeepSeek 模型名 |
| `AI_COACH_LLM_TIMEOUT` | `20` | LLM 调用超时(秒) |

## 9. 联系人 / 仓库

- 算法仓库：`ai-coach-algorithm-W1`
- 算法负责：xinanQ
- 算法主干文档：[docs/system_overview.md](system_overview.md)
- 接口适配器实现：[app/api/dialog_presenter.py](../app/api/dialog_presenter.py)
