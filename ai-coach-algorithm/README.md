# AI Coach Algorithm

金融绩效驱动 AI 陪练算法底座。系统设计原则：**算法做识别和检测，LLM 做生成和判断**。

```text
marketing_chunks.json
-> 中文 sentence-transformers embedding (BAAI/bge-small-zh-v1.5)
-> Chroma 持久化向量库（tutor / customer 双 collection）
-> 双路 RAG 检索
     -> 导师侧：HyDE 锚定 rubric must_points -> LLM 4 维度评分
     -> 客户侧：意图 gap 检测 -> LLM 模拟客户追问
-> 算法辅助信号（gap / coverage / retrieval）
-> Redis / PostgreSQL 记忆（JSON 兜底）
-> 接口层 presenter 适配联调合约
```

## 已实现能力

**RAG 双路**
- 默认真实中文 embedding：`BAAI/bge-small-zh-v1.5`，本地模型不可用时降级到 `local_hash_embedding_v1`。
- Chroma 持久化向量库，`tutor` / `customer` 双路 collection。
- 导师侧 HyDE 锚定 rubric must_points 检索；客户侧意图 gap 驱动检索。

**LLM 评分 + LLM 客户模拟（DeepSeek 接入）**
- 4 维度评分（合规度 / 异议处理 / 逻辑结构 / 共情力），不再是单一总分。
- LLM 评分基于完整对话轨迹（不只看最后一轮），认可改正行为，红线一票否决。
- LLM 模拟客户：根据画像 + 对话历史 + gap 分析 + RAG 检索自然生成追问，告别模板重复。
- 自然语言改进 suggestion（不是模板套话）。
- 任何 LLM 失败自动回退规则评分 / 模板追问，对调用方透明。

**意图理解**
- 6 标签多标签分类（rate / liquidity / safety / procedure / rejection / compliance）。
- 关键词基线 + BERT-mini adapter 预留（当前 BERT 因样本不足禁用，纯关键词跑）。
- 阈值经标定回填（覆盖阈值 0.36，来自 193 条 gold 数据集）。

**接口与对接**
- 对话 `start → reply → finish` 闭环，对齐《微信小程序接口联调说明》。
- presenter 适配器把算法 snake_case 翻译成联调 camelCase + 业务字段 mock。
- `/dialog/finish` 的 `source` 字段动态反映最终评分实际用了 `LLM_BASED` 还是 `RULE_BASED`。

**记忆与兜底**
- Redis 短期 + PostgreSQL 长期记忆 adapter，JSON 安全兜底。
- 无 DeepSeek key、无 Redis、无 PG 都能跑通 demo（自动降级）。

## 关键 API

- `GET /health`
- `POST /rag/marketing/vector-index/build`
- `GET /rag/marketing/vector-index/status`
- `POST /rag/marketing/vector-retrieve`
- `POST /rag/marketing/customer-answer-understanding`
- `POST /marketing-tutor/prompt-context`
- `GET /dialog/profiles`
- `GET /practice/tasks`
- `GET /practice/tasks/{task_id}`
- `POST /dialog/start`
- `POST /dialog/reply`
- `POST /dialog/finish`
- `GET /memory/status`
- `GET /memory/session/get`
- `POST /memory/session/upsert`
- `GET /memory/longterm/list`
- `POST /memory/rag-history/retrieve`

## 环境变量

```powershell
$env:AI_COACH_EMBEDDING_BACKEND="sentence_transformers"
$env:AI_COACH_EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"
$env:AI_COACH_CHROMA_MAX_QUERY_RESULTS="80"   # Chroma 单次召回上限；调低可换取更低延迟
$env:AI_COACH_REDIS_URL="redis://localhost:6379/0"
$env:AI_COACH_POSTGRES_DSN="postgresql://user:password@localhost:5432/ai_coach"
$env:AI_COACH_SHORT_MEMORY_BACKEND="auto"
$env:AI_COACH_LONG_MEMORY_BACKEND="auto"

# LLM 评分 + LLM 模拟客户（DeepSeek，可选；不设则自动走规则/模板兜底）
$env:DEEPSEEK_API_KEY="sk-xxx"
$env:AI_COACH_SCORER="llm"          # llm（默认）/ rule       — 评分用 LLM 还是规则
$env:AI_COACH_CUSTOMER_LLM="llm"    # llm（默认）/ template   — 客户追问用 LLM 还是固定模板
$env:AI_COACH_LLM_MODEL="deepseek-chat"
$env:AI_COACH_LLM_TIMEOUT="20"
```

未配置 Redis/PostgreSQL 时，系统会自动使用 `mock_db/*.json`，接口仍可正常联调。
未配置 `DEEPSEEK_API_KEY` 时：
- 评分自动回退到规则评分器（4 维度仍可用），`source` 返回 `RULE_BASED`。
- 客户追问自动回退到 `CUSTOMER_INTENT_PROBES` 模板（gap 驱动的固定句式）。

## 任务首页数据（算法侧 demo/catalog）

小程序任务页如果要做成“任务等级 + 训练方向 + 推荐场景卡片”的样式，可先接算法侧任务目录接口：

```text
GET /practice/tasks
GET /practice/tasks?direction=objection
GET /practice/tasks/{taskId}
GET /practice/tasks/{taskId}/scripts
GET /practice/scripts/{scriptId}?taskId={taskId}
```

`/practice/tasks` 返回页面可直接消费的展示字段：
- 默认从 39 个客户画像动态生成 39 个训练任务卡，并按 7 个训练方向分类
- `levelName` / `points` / `target` / `streakDays` / `weekGain`：成长卡片 demo 字段
- `tabs`：上级下发 / 自主任务 / 已完成
- `directions`：客户触达 / 需求识别 / 产品讲解 / 异议处理 / 成交促成 / 合规风险 / 售后维护
- `list[].tags`：中文展示标签
- `list[].intentTags`：算法内部英文 intent code，供调试或后端映射使用
- `list[].sceneId` / `list[].customerId`：启动陪练时传给 `/dialog/start`

示例：

```json
{
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
      "durationText": "8分钟",
      "description": "分红演示和实际差距、现金价值过低、封闭期太长。"
    }
  ]
}
```

说明：39 条任务卡来自 `data/customer_profiles.json` 的 39 个客户画像；成长等级、积分、任务完成状态等仍建议最终由 Java 后端业务库接管。算法侧接口用于联调、推荐场景目录和中文标签展示。

任务详情页可直接使用 `scriptEntry` 渲染“查看标准话术”按钮，点击后调用 `/practice/tasks/{taskId}/scripts`。话术卡片返回 `scriptId`、`title`、`subtitle`、`tags`、`standardSpeech`、`copyText`、`sourceFile` 等字段；详情页可调用 `/practice/scripts/{scriptId}?taskId={taskId}`，用于实现“话术详情 / 复制标准话术”的页面。

## Docker 开发环境（算法服务 + Redis + PostgreSQL）

本地如果已经安装 Docker，可以一键启动算法服务和依赖服务：

```powershell
docker compose up -d
```

启动后打开：

```text
http://127.0.0.1:8000/docs
```

查看健康状态：

```powershell
curl http://127.0.0.1:8000/health
```

开发环境的 compose 会同时启动：
- `ai-coach-api`：FastAPI 算法服务，端口默认 `8000`
- `ai-coach-redis`：短期 session 记忆，端口默认 `6379`
- `ai-coach-postgres`：长期训练记忆，端口默认 `5432`

Docker 内部使用服务名连接依赖：
- `AI_COACH_REDIS_URL=redis://redis:6379/0`
- `AI_COACH_POSTGRES_DSN=postgresql://ai_coach:ai_coach_dev@postgres:5432/ai_coach`

为了让新同事第一次启动更快，Docker 开发环境默认使用 `hash` embedding，不会下载中文 embedding 模型。需要切回真实中文 embedding 时，在启动前设置 Docker 专用变量：

```powershell
$env:AI_COACH_DOCKER_EMBEDDING_BACKEND="sentence_transformers"
$env:AI_COACH_DOCKER_EMBEDDING_MODEL="BAAI/bge-small-zh-v1.5"
docker compose up -d --build
```

如果本机端口冲突，可以改端口：

```powershell
$env:AI_COACH_API_PORT="18000"
$env:AI_COACH_REDIS_PORT="16379"
$env:AI_COACH_POSTGRES_PORT="15432"
docker compose up -d
```

如果 Docker Hub 拉取 `python:3.11-slim` 超时，可以先重试：

```powershell
docker pull python:3.11-slim
docker compose up -d --build
```

如果网络环境必须走公司镜像源或内部 registry，可以只替换基础镜像：

```powershell
$env:AI_COACH_PYTHON_IMAGE="你的镜像源/library/python:3.11-slim"
docker compose up -d --build
```

停止服务：

```powershell
docker compose down
```

清空 Redis/PostgreSQL 本地数据卷（会删除本地容器数据库数据）：

```powershell
docker compose down -v
```

本机未安装 Docker 时也不影响算法 demo，系统仍可自动走 JSON fallback。

## 启动

```powershell
# 配置 DeepSeek key（启用 LLM 评分 + LLM 客户模拟；不配也能跑，会自动回退）
$env:DEEPSEEK_API_KEY = "你的_DeepSeek_API_KEY"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开：

```text
http://127.0.0.1:8000/docs
```

## 试用流程（5 分钟跑通完整陪练）

> ⚠️ API key 在本地终端用环境变量设置即可，**不要写进任何代码或文档**。生产环境用 secrets 管理（如 Vault、AWS Secrets Manager、GitHub Actions secrets）。

### Step 1 · 启动对话 `POST /dialog/start`

```json
{
  "user_id": "U_DEMO",
  "scene_id": "INS_PERIODIC",
  "total_rounds": 5
}
```

返回里复制 `sessionId` 留用。AI 客户的开场白来自画像配置（"流动性担忧型"客户）。

### Step 2 · 第 1 轮回复 `POST /dialog/reply`

```json
{
  "session_id": "<上一步的 sessionId>",
  "employee_message": "我先了解您的资金安排,这款期交保险需要每年持续缴费,请以保险合同为准。"
}
```

**观察点：**
- `reply` 只返回 AI 客户追问，不再返回 `liveScore` / `source`；最终分数统一在 `/dialog/finish` 计算
- `message.content` → LLM 会**揪你刚才说的话**反问（比如"你光说以合同为准,那合同里到底..."），不再是固定模板

### Step 3 · 第 2 轮回复（补充方案）

```json
{
  "session_id": "<sessionId>",
  "employee_message": "您不用担心,我们这款产品有现金价值,中途如果需要可以申请保单贷款或者部分领取应急,具体扣多少钱要看您持有了多久,前几年退保确实会有损失,但贷款不影响保单效力。"
}
```

**观察点：**
- AI 客户**不会重复上一轮的问题**
- AI 客户会**抓住"保单贷款"接着追问**（比如"那贷款利息怎么算?比银行高不高?"）

### Step 4 · 第 3 轮： 故意踩 5 个合规雷

```json
{
  "session_id": "<sessionId>",
  "employee_message": "您放心,这款产品稳赚不赔,我们大公司绝对保证您的本金安全,跟存款一样的,而且收益比定期存款高,买了就是赚到。"
}
```

埋的雷：稳赚不赔 / 绝对保证 / 大公司 / **跟存款一样**（银保监最严违规）/ 买了就是赚到。

**观察点（最有说服力的一步）：**
- AI 客户**当场反击**，会直接揪"跟存款一样"质问（比如"保险怎么能跟存款一样呢?你能保证一分不少拿出来吗?"）
- `/dialog/finish` 的最终评分会基于完整对话识别这类合规红线；如果没有后续纠错，合规度会明显受影响

### Step 5 · 第 4 轮：员工挽救（可选但推荐）

```json
{
  "session_id": "<sessionId>",
  "employee_message": "抱歉,我刚才表述不准确。保险和存款是不同的产品,具体收益、领取条件和现金价值都要以合同条款为准。这款产品如果您需要中途用钱,可以通过保单贷款,但本金能否完全收回取决于持有时长。"
}
```

**观察点：**
- AI 客户**语气缓和**（检测到员工承认错误）
- `/dialog/finish` 的最终建议会结合完整轨迹，认可纠错行为，而不是只看最后一句

### Step 6 · 结束对话 `POST /dialog/finish`

```json
{ "session_id": "<sessionId>" }
```

**观察点（最关键的一步）：**

返回包含：
- `score` —— 综合分（基于**完整对话轨迹**，不只看末两轮）
- `dimensionScores` —— 4 维度：合规度 / 异议处理 / 逻辑结构 / 共情力
- `weakTags` —— LLM 精准弱点标签（如"合规红线/绝对化承诺/共情缺失"）
- `suggestion` —— **真正的销售辅导建议**（不是模板套话）
- `source` —— `LLM_BASED` 表示 DeepSeek 完成最终评分，`RULE_BASED` 表示已降级到规则评分

如果 Step 5 挽救了，suggestion 会**认可纠错行为**；如果没挽救，合规度会被打到 0 分。

### 切换场景试试不同性格客户

| `scene_id` | 客户人设 | 适合演示什么 |
|---|---|---|
| `INS_PERIODIC` | 流动性担忧型 | 期限/退保/缴费压力 |
| `INS_DIVIDEND` | 收益敏感型 | 分红不确定性、保险 vs 理财 |
| `FUND_OBJECTION` | 风险厌恶型 | 本金安全、净值波动 |
| `INS_GENERAL` | 拒绝犹豫型 | 共情技巧、不强推 |

每个场景的 AI 客户人设、追问角度、容忍度都不同——同一段员工话术在不同场景下评分可能差很多。

### 排查：finish source 一直显示 RULE_BASED

LLM 调用失败时系统会静默回退到规则评分，看启动 uvicorn 的终端有没有 `WARNING: LLM scoring call failed: ...` 日志：

| 错误 | 原因 | 修复 |
|---|---|---|
| `401 Unauthorized` | key 错或没读到 | 在**启动 uvicorn 的终端**里重新设 `$env:DEEPSEEK_API_KEY="sk-xxx"`，再重启服务 |
| `Insufficient Balance` | 账户余额不足 | 去 [platform.deepseek.com](https://platform.deepseek.com/) 充值 |
| `Request timeout` | 网络慢 | `$env:AI_COACH_LLM_TIMEOUT="40"` 改长超时 |

## 构建向量库

默认使用中文 embedding：

```powershell
@'
from app.core.embedding_builder import build_marketing_vector_index
print(build_marketing_vector_index(force=True))
'@ | .\.venv\Scripts\python.exe -
```

离线测试使用 hash fallback：

```powershell
@'
from app.core.embedding_builder import build_marketing_vector_index
print(build_marketing_vector_index(force=True, embedding_backend="hash", dimensions=64))
'@ | .\.venv\Scripts\python.exe -
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 意图标注 → 标定 → 训练 → 评测 工作流

客户侧 gap 检测、导师侧 must_point 覆盖度的阈值，以及 BERT-mini 意图分类器，都依赖一份人工标注的意图数据集。标注规范见 [docs/intent_annotation_schema.md](docs/intent_annotation_schema.md)。

### 第 1 步：生成待标注候选

```powershell
.\.venv\Scripts\python.exe -m app.core.intent_eval_set_builder --target-size 250
```

产出 `data/intent_eval_candidates.jsonl`（自然语料抽样，`suggested_labels` 为关键词建议）。

### 第 2 步：人工标注

逐条编辑，把真实意图填进 `gold_labels`，并把 `needs_review` 改为 `false`：

```jsonc
{"id": "IE_0003", "text": "我再考虑考虑吧", "gold_labels": ["rejection_or_hesitation"], "needs_review": false}
{"id": "IE_0010", "text": "您好请问几点了",  "gold_labels": [], "needs_review": false}   // 无关句留空数组
```

- 多标签用数组；无关句留 `[]`（有用的负样本）。
- 建议另存为 `data/intent_eval_gold.jsonl`，给稀缺标签（`procedure_question` / `compliance_sensitive`）和员工话补写样本。
- 未标注的行会自动用 `suggested_labels` 占位，流程可先空跑，但数字不可信（会有 warning）。

### 第 3 步：切分 + 标定 + 训练 + 评测

```powershell
# 切分 train/eval (70/30)
.\.venv\Scripts\python.exe -m app.core.intent_dataset_prep --input data/intent_eval_gold.jsonl

# 标定意图存在阈值（扫阈值找最优 micro-F1）
.\.venv\Scripts\python.exe -m app.core.intent_threshold_calibrator --input data/intent_eval_gold.jsonl

# 训练 BERT-mini 多标签分类头（产出 models/bert_mini_intent/）
.\.venv\Scripts\python.exe -m app.core.bert_mini_trainer --train-file data/intent_train.jsonl

# 对比 keyword baseline vs BERT-mini 在 eval 集上的 F1
.\.venv\Scripts\python.exe -m app.core.intent_model_eval
```

训练后模型放在 `models/bert_mini_intent/`，意图推理会自动从 keyword fallback 切到 BERT-mini（`analyze_customer_answer` 的 `bert_mini_available` 字段会变 `true`）。

> 注意：标定脚本给出的最优阈值，需要手动回填到代码——意图覆盖阈值在 `app/core/coverage.py` 的 `update_covered_intents`，must_point 覆盖阈值在 `app/core/marketing_rag.py` 的 `TUTOR_MUST_POINT_THRESHOLD`。

## 评测体系

### E2E (端到端) 评测

E2E 评测模拟完整的陪练对话流程，验证从 `start_dialogue` → 多轮 `reply_dialogue` → `finish_dialogue` 的整个链路。

**运行方式：**

```powershell
# 完整评测（包括 E2E）
.\.venv\Scripts\python.exe -m eval.run_all --stages all

# 仅 E2E 评测
.\.venv\Scripts\python.exe -m eval.stages.eval_e2e --sample-size 10 --verbose
```

**评测维度：**

| 指标 | 说明 | 目标 |
|------|------|------|
| `contract_pass` | 接口契约符合性（reply 不返回 liveScore/source） | 100% |
| `intent_pass` | 意图识别合理性 | > 80% |
| `gap_pass` | 漏答项计算准确性 | > 90% |
| `retrieval_hit` | RAG 上下文包含关键知识 | > 70% |
| `followup_pass` | AI 客户追问方向符合预期 | > 75% |
| `finish_score_pass` | 最终分数落在合理区间 | > 80% |
| `strict_score_pass` | 最终分数落在更窄业务校准区间 | > 80% |
| `weak_tag_pass` | 弱点标签命中相关性 | > 70% |
| `e2e_overall_pass` | 综合通过率 | > 60% |
| `strict_e2e_overall_pass` | 严格综合通过率，用于防止 gold 区间过宽 | > 60% |

当前基线（2026-07-06）：E2E gold 已扩展到 50 条，并为部分容易过宽的评分 case 增加 `strict_score_range`。主报告仍看标准 `e2e_overall_pass`，同时用 `strict_e2e_overall_pass` 观察真实业务校准压力。当前主链路短板主要在 finish 最终评分校准。

详细文档：[docs/algorithms/08_e2e_evaluation.md](docs/algorithms/08_e2e_evaluation.md)

### 单阶段评测

```powershell
# RAG 检索评测（主指标 final_context_recall@8，保留 recall@3/5/8 诊断项）
.\.venv\Scripts\python.exe -m eval.stages.eval_retrieval --verbose

# Must point 覆盖度评测（含 negative pattern 检测）
.\.venv\Scripts\python.exe -m eval.stages.eval_must_point --verbose

# LLM intent 检测评测
.\.venv\Scripts\python.exe -m eval.stages.eval_llm_intent --sample 50
```

详细文档：[docs/algorithms/07_rag_evaluation.md](docs/algorithms/07_rag_evaluation.md)
