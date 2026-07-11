# ai-coach-algorithm 企业级优化路线图（单人执行版）

> **状态更新（2026-07-11）**：Phase 0/1（口径与评估可信度）已全部完成并超出原计划——
> 评估体系已重构为三链路（组件级 / 动态对话 / 固定 Transcript 评分器），评分器基线
> 0.92–0.94 已冻结（指纹+门禁守护），followup 审计完成（详见 docs/evaluation_ops_guide.md）。
> 本文件中涉及"E2E 0.96 守护"的旧口径描述已由 v2 指标契约取代，仅作历史记录保留。
> 当前活跃工单：followup 尺子修缮（ops_guide §5）→ 弱点标签去噪。

> 基于 2026-07-09 全模块审计（分支 `feature/ai-coach-algorithm-dev`）。单人推进，串行执行。
> 原则：主链路 E2E 0.96 是底线，任何改动先跑 `python -m eval.run_all --stages all` 确认无回归再合入；所有优化小步提交、可回滚。
> 单人执行铁律：每天收工前工作区必须干净（当天改动当天提交），避免再次出现多文件 WIP 悬空。

## 现状基线（改动前锁定）

| 指标 | 当前值 | 说明 |
|---|---|---|
| e2e_overall_pass | 0.96 | strict 口径 0.94 |
| finish_score_pass | 1.00 | strict 0.98 |
| llm_only_micro_f1（intent 独立评估） | 0.7576 | recall 0.694，为当前 bottleneck |
| reranked_recall@3（customer 路由） | 0.489 | 客户侧检索短板 |
| reranked_recall@3（tutor 路由） | 0.710 | |
| must_point point_f1 | 0.8376 | 基于 local_hash 校准 |
| embedding 实际后端 | **local_hash（fallback）** | 请求的 bge-small-zh 加载失败 |

---

## Phase 0：口径与仓库卫生（本周内，0.5-1 天）

**目标：让现有成果"说得清、丢不了、拉得干净"。**

### 0.1 提交 WIP（P0）
- 现状：`rule_scorer.py`（+129 行校准层）、`README.md`、`02_scoring.md`、`report.json` 未提交，存在丢失风险。
- 做法：先跑全量 eval 确认无回归 → `git add -A && git commit` → push `origin feature/ai-coach-algorithm-dev`。
- 验收：`git status` 干净；report.json 中 e2e ≥ 0.96。

### 0.2 仓库清理（P0，命令已备好）
```bash
git rm -r --cached ai-coach-algorithm/ai-coach-algorithm
git rm --cached ai-coach-algorithm/data/eval/retrieval_verbose.json
rm -rf ai-coach-algorithm/ai-coach-algorithm
```
- `.gitignore` 已补 `ai-coach-algorithm/`（嵌套目录）与 `data/eval/retrieval_verbose.json` 两条规则。

### 0.3 Embedding 基线声明（P0）
- 现状：eval 与运行时实际都在 local_hash embedding 上（bge-small-zh 下载失败自动 fallback），但文档口径写的是 bge。指标与环境不符是答辩/验收最大风险。
- 做法：在 README 与 `docs/algorithms/08_e2e_evaluation.md` 显式声明"V1 指标基线 = local_hash_embedding_v1"；eval 报告输出时若 `runtime_info.embedding.is_fallback=true`，在 ASCII 表头打印醒目 WARNING。
- 验收：任何人看 report 都能知道指标跑在哪个 embedding 上。

### 0.4 intent 双口径说明文档（P1）
- 现状：独立评估 F1 0.76 vs e2e intent_pass 1.00，`component_quality_estimate 0.46` 与 `end_to_end_estimate 0.96` 并排出现无解释。
- 做法：在 08_e2e_evaluation.md 增加"指标口径对照表"：e2e = 预期意图集合命中（宽），独立评估 = 逐标签 micro F1（严）；说明 bottleneck 字段只反映组件级口径。
- 验收：汇报 PPT 可直接引用该表。

---

## Phase 1：评估可信度加固（第 1-2 周，2-3 天）

**目标：指标经得起追问，杜绝"过拟合 eval"质疑。**

### 1.1 held-out 泛化集（P0 级重要性）
- 现状：rule_scorer 新增的 `_business_quality_profile` 关键词地板值与 e2e gold 高度相关，存在过拟合风险（rule_scorer.py:558-639 大量 `max(score, N)` 硬地板）。
- 做法（单人版，防"自己出题自己考"）：
  1. 新建 `data/eval/e2e_holdout_gold.jsonl`（20-30 条）。素材来源按优先级：真实试用/联调对话记录 > 用 LLM 对现有 gold 做口语化改写（换措辞不换语义，再人工校对）> 隔几天凭场景记忆盲写（写时不看现有 gold 和 rule_scorer 词表）；
  2. eval 增加 `--stages e2e_holdout`，报告单列 holdout 指标；
  3. holdout **只做验收，不做调参依据**——写完后不再打开细看失败 case 的关键词，只看通过率。这条规矩写进文档，防止无意识地把 holdout 调成第二个训练集。
- 验收：holdout e2e_overall_pass ≥ 0.85（低于此值说明规则过拟合，需回调）。

### 1.2 rule_scorer 配置化（P1）
- 现状：地板/封顶值、关键词表硬编码在 `rule_scorer.py`，调参 = 改代码，审查困难。
- 做法：把 `_business_quality_profile` 的 8 组词表、各 `max/min` 阈值迁到 `configs/scoring_weights.yaml`（已有该文件，扩展 schema）；rule_scorer 启动时加载，保留代码内默认值兜底。
- 验收：改词表不动 `.py` 文件；全量 eval 结果与迁移前 bit 级一致（先做等价迁移，再谈调参）。

### 1.3 bge embedding 修复 + A/B（P1）
- 做法：
  1. 离线下载 `BAAI/bge-small-zh-v1.5` 到 `model_cache/`（已在 .gitignore），`embedding_adapter` 支持 `AI_COACH_EMBEDDING_LOCAL_PATH` 指向本地目录，杜绝运行时联网下载；
  2. 用 bge 重跑全量 eval，与 hash 基线出对比表（重点看 customer 路由 recall 与 must_point F1）；
  3. **只有 bge 全面不劣于 hash 且 must_point 阈值重校准通过后**，才切默认后端；联调窗口期内保持 hash。
- 验收：两份 report 并存于 `data/eval/`，命名含 backend 标识。

### 1.4 失败案例自动归因（P2）
- 现状：verbose trace 已有（`e2e_verbose_*.json`），但 report.json 无 case 级摘要。
- 做法：`eval/report.py` 增加 `failures` 段：每个未通过 case 的 id、失败 stage、expected vs actual（分数带/命中 chunk）。
- 验收：看 report.json 即可定位 0.96 里那 2 个失败 case 的原因，不用翻 verbose 文件。

---

## Phase 2：算法质量提升（第 2-3 周，3-5 天）

**目标：把两个已量化的短板补上。**

### 2.1 customer 路由检索优化（P1，最大算法收益点）
- 现状：customer 路由 reranked_recall@3 = 0.489（tutor 0.710），客户追问的 RAG 支撑不足；rerank 对该路由几乎无增益（ceiling@3 = 0.489，说明瓶颈在召回而不是排序）。
- 做法（按投入产出排序）：
  1. **查询改写**：客户追问检索的 query 目前偏短语化，拼接 `intent 中文标签 + 客户顾虑关键词` 扩展 query（改 `marketing_rag.py` 的 customer 路由查询构造）；
  2. **route 专属 fusion 权重**：customer 路由提高关键词通道权重（客户口语与 chunk 书面语的语义 gap 大，hash 向量下关键词更可靠）；用 `eval/sweep.py` 网格搜索，只对 customer 路由生效；
  3. 若 1.3 的 bge A/B 显示 customer 路由显著受益，切换即是最大杠杆。
- 验收：customer reranked_recall@3 ≥ 0.65，且 tutor 路由与 e2e 不回退。

### 2.2 intent 识别提升（P1）
- 现状：llm_only recall 0.694——漏检为主。
- 做法：
  1. 分析 `llm_intent_eval.json` 漏检分布，按标签统计（通常集中在 2-3 个易混标签）；
  2. 对 top 漏检标签在 LLM prompt 中补充判别边界示例（few-shot，改 `app/core/llm/prompts/` 下 intent prompt）；
  3. gold 从 50 条扩到 100+ 条（可用 LLM 批量生成候选 + 人工快速校对，半天可完成），降低单条波动；
  4. 备选：`bert_mini_intent_classifier` 已有训练管线，若 LLM 调优到 0.85 仍不够再启用本地模型混合。
- 验收：llm_only_micro_f1 ≥ 0.85，recall ≥ 0.80。

### 2.3 must_point 锚定鲁棒性（P2）
- 现状：point_precision 0.76（误判"已覆盖"偏多），阈值 0.35 为 hash 校准。
- 做法：poor 组全 0 说明判负能力强；针对 precision，检查 `coverage.py` 的语义相似匹配在 hash 向量下的假阳性 case（must_point_verbose 已有素材），必要时提高 sem 阈值并用 kw 兜底。
- 验收：point_precision ≥ 0.85 且 recall 不低于 0.90。

---

## Phase 3：工程化企业级改造（第 3-4 周，3-4 天）

**目标：可观测、可部署、可交接。**

### 3.1 可观测性（P1）
- 现状：`main.py` 无日志中间件、无 trace_id、无统一异常处理；排查线上问题只能靠 uvicorn 默认日志。
- 做法：
  1. 新增 `app/middleware.py`：请求级中间件生成/透传 `X-Trace-Id`（Java 侧头部有则复用），响应头回写；
  2. 结构化日志（JSON lines）：trace_id、path、耗时 ms、session_id、scorer source、LLM 调用耗时/是否 fallback；LLM fallback 发生时必须 WARN 级记录原因；
  3. 全局异常 handler：500 时返回 `{"detail", "traceId"}`，日志记完整栈；
  4. `/health` 已很好（含 memory/vector_store 状态），补充 `llm: {configured: bool, model: str}`（不回显 key）。
- 验收：一次联调失败能凭 trace_id 在日志中还原完整调用链。

### 3.2 Docker 镜像瘦身（P1）
- 现状：单阶段构建，torch+transformers 全量进镜像（估计 5GB+），而 Docker 运行时用 hash embedding 根本不需要 torch。
- 做法：
  1. requirements 分层：`requirements.txt`（运行必需：fastapi/uvicorn/pydantic/numpy/chromadb/redis/psycopg/openai/json-repair）+ `requirements-ml.txt`（torch/transformers/sentence-transformers，本地实验用）+ `-r requirements.txt` 引用；
  2. Dockerfile 默认只装运行层；加 build arg `INSTALL_ML=0` 可选装 ML 层；
  3. 多阶段构建 + 非 root 用户（`USER app`）；build-essential 只留在 builder 阶段。
- 验收：镜像 < 800MB；`docker compose up` 后 /health 全绿、E2E smoke 通过。

### 3.3 服务鉴权（P1，生产前必须）
- 做法：简单方案即可企业达标——`AI_COACH_API_TOKEN` 环境变量 + FastAPI dependency 校验 `Authorization: Bearer`；不设 token 时保持开放（开发模式）并在启动日志 WARN。Java 侧 `AiCoachClient` 加一个 header，一行改动。
- 验收：设 token 后无凭证请求返回 401；compose 与 .env.example 补该变量。

### 3.4 测试金字塔补齐（P1）
- 现状：仅 1 个测试文件 6 个用例。
- 补充清单（约 1.5 天）：
  1. `tests/test_dialog_contract.py`：presenter 三接口字段快照（camelCase 键集合断言 + reply 无 liveScore/source + finish 必含 7 字段）——这是防契约回退的核心护栏；
  2. `tests/test_rule_scorer.py`：合规 hard cap（保本保息 → total < 30）、corrected_compliance 路径、空回答/超长回答边界；
  3. `tests/test_coverage.py`：must_point 命中/漏检各 3 例；
  4. `tests/test_round_policy.py`：6/8/10 轮边界与 `finished` 判定。
- 验收：`pytest` < 60s 全绿（不依赖网络/LLM，LLM 路径用 monkeypatch 断网即验 fallback）。

### 3.5 CI（P2）
- 做法：GitHub Actions（团队仓库）：push 到 feature 分支跑 `pytest` + `ruff check`；nightly 或手动触发跑 `eval.run_all`（LLM stage 用 cached）。
- 验收：PR 页面可见测试状态。

---

## Phase 4：长期增强（第 4 周后，按需）

1. **LLM 评分一致性审计**：抽 30 条对话双跑 llm/rule scorer，统计分差分布；分差 > 15 的 case 人工裁决，形成评分校准集。目标：两 scorer 均值差 < 8 分，保证 LLM 超时降级时用户体感分数不跳变。
2. **数据回流闭环**：真实联调对话（脱敏）→ 定期转成 gold 候选 → 人工标注 → 扩充 eval 集。这是指标从"自造 gold"走向"真实分布"的关键一步。
3. **意图模型本地化**：若 LLM intent 成本/时延成为问题，启用已有 `bert_mini_*` 管线训练本地分类器做初筛，LLM 只裁决低置信 case。
4. **记忆个性化深化**：weakness_profile 已有，可在 /dialog/start 的开场白注入"上次弱点"定向出题（adaptive_difficulty 已具备难度维度，扩展到内容维度）。
5. **生产部署形态**：去掉 compose 里的 `--reload` 与源码 volume 挂载（当前是开发形态）；出一份 `docker-compose.prod.yml`（无挂载、限 CPU/内存、日志 driver）。

---

## 验收总表（企业级达标线）

| 维度 | 达标标准 |
|---|---|
| 契约 | 契约单测护栏存在；文档-代码-测试三方一致 |
| 评估 | holdout 集通过；report 自带失败归因；embedding 口径显式 |
| 算法 | customer recall@3 ≥ 0.65；intent F1 ≥ 0.85；e2e ≥ 0.96 不回退 |
| 可观测 | trace_id 全链路；LLM fallback 有 WARN 日志；/health 全维度 |
| 安全 | token 鉴权；无密钥入库（已达标）；日志不含用户敏感原文 |
| 交付 | 镜像 < 800MB；pytest < 60s；新人按 README 30 分钟起服务 |

## 单人逐周执行表（串行，每项独立提交）

**第 1 周：口径钉死 + 护栏建立**（Phase 0 全部 + 1.1 + 3.4 的契约测试）
| 天 | 任务 | 产出/提交 |
|---|---|---|
| D1 上午 | 跑全量 eval → 提交 WIP + 仓库清理 | 1 个 commit，工作区清零 |
| D1 下午 | embedding 基线声明 + fallback WARNING | README/08 文档 + report 改动 |
| D2 | intent 双口径对照表；presenter 契约快照测试 | 08 文档 + `test_dialog_contract.py` |
| D3-D4 | held-out 集 20-30 条 + `--stages e2e_holdout` | gold 文件 + eval 改动 + 首次 holdout 报告 |
| D5 | rule_scorer 单测（hard cap/边界）+ 机动缓冲 | `test_rule_scorer.py` |

**第 2 周：评估加固 + 算法短板 I**（1.2 + 1.3 + 2.1 启动）
| 天 | 任务 | 产出/提交 |
|---|---|---|
| D1 | rule_scorer 词表/阈值迁 yaml（等价迁移，eval bit 级一致） | 配置化 commit |
| D2 | bge 离线加载修复 + hash/bge A/B 报告 | 两份 report + 结论写进文档 |
| D3-D5 | customer 路由：查询改写 → sweep fusion 权重 → 验收 recall@3 ≥ 0.65 | marketing_rag 改动 + sweep 结果 |

**第 3 周：算法短板 II + 工程化**（2.2 + 3.1 + 3.2）
| 天 | 任务 | 产出/提交 |
|---|---|---|
| D1-D2 | intent：漏检分布分析 → prompt few-shot → gold 扩到 100 条 → F1 ≥ 0.85 | prompt + gold commit |
| D3 | trace_id 中间件 + 结构化日志 + 全局异常 handler | `app/middleware.py` |
| D4 | requirements 分层 + Dockerfile 多阶段 + 非 root | 镜像 < 800MB 验证 |
| D5 | token 鉴权 + compose/env 文档更新 + 机动缓冲 | 鉴权 commit |

**第 4 周（如有）：收尾**：2.3 must_point precision、1.4 失败归因、3.5 CI、compose 生产形态。时间不够则全部降级为 backlog——它们不影响验收底线。

**如果只剩 3 天**（最小企业级路径）：第 1 周的 D1-D2 全做 + held-out 集压缩到 15 条 + 3.3 鉴权。其余进 backlog。
