# 评估体系运行手册（v2 补充机制）

> 本文档记录 2026-07-10/11 新增的四个评估保障机制的用法与口径约定，
> 以及 followup 审计的结论。指标定义见 docs/algorithms/08_e2e_evaluation.md。

## 1. 评分器冻结基线与配置指纹

正式基线：**50 条人工审定固定对话，score_band_pass 0.92–0.94（temp-0 运行区间），
mean_band_distance ≤0.3，50/50 LLM 评分，transcript 完整性 1.0。已冻结。**

冻结由两个哈希强制执行：
- `transcript_hash`：绑定带宽到对话文本（gold 内嵌）；
- `scorer_config_fingerprint`（eval/scorer_fingerprint.py）：绑定基线到评分器配置
  （模型/温度/max_tokens/渲染后静态 Prompt/红线词表/9 个评分关键源文件哈希）。

任何评分相关改动（含注释）→ 指纹失配 → 报告 `baseline_fingerprint_match=false`
且 `citable_full_baseline=false`。重新认证流程：

```powershell
python -m eval.stages.eval_scorer --bless-fingerprint   # 仅允许全量、LLM-only 运行
```

约定：**不围绕个别 MISS 调参**。temp-0 下存在 ±1~2 个 case 的 run 间漂移，
对外引用写区间（0.92–0.94），不写单次值。

## 2. 回归门禁

```powershell
python scripts/regression_gate.py --skip-scorer   # 离线免费：gap/retrieval/must_point
python scripts/regression_gate.py                 # 含 scorer 门禁（需 DEEPSEEK_API_KEY）
```

阈值在 data/eval/regression_thresholds.json：gap≥0.88、retrieval≥0.78、
must_point≥0.80、scorer≥0.90（低于基线区间下沿，防漂移误报）+ 完整性=1.0 +
指纹漂移即失败。**任何触碰评分/检索/prompt/eval 的改动，合并前必须跑门禁。**
降低任何地板值需在该 JSON 中写明理由。

## 3. 动态指标多运行口径

动态链路（LLM 客户，温度 0.7）单次运行只是采样：

```powershell
python -m eval.stages.eval_e2e --runs 3   # 每指标报 mean/min/max，headline 取均值
```

单次运行自动标记 `single_run_not_citable=true`，不得对外引用。

## 4. Follow-up 校验器可信度审计（2026-07-10 结论）

工作流：

```powershell
python -m eval.stages.eval_e2e --verbose --save-trace   # trace 含逐轮 followup 判定
python scripts/build_followup_audit.py                  # 抽取失败轮 → followup_audit.jsonl
# 人工/AI辅助填 verdict: generation | gold | checker，重跑 build 脚本看三分类
```

**审计结论（29 条失败轮，候选判定 + 人工抽检）：
generation 0 条 / gold 18 条 / checker 11 条。**

含义：followup_pass 0.54 基本是测量误差，客户追问生成质量本身良好
（失败轮多为客户正确死磕员工未回答的问题）。结构性根因：
`expected_direction` 按"员工回答了上一问"的理想脚本编写，与
"gold 员工脚本故意答得差"（评分测试点）互斥。

**由此，"客户追问质量提升 0.50→0.75"立项改判为"followup 尺子修缮"**，见 §5。

## 5. 工单：followup 尺子修缮（2026-07-11 执行中）

按审计证据排序：

1. ✅ **通用规则**（checker 侧）：客户重申本对话中未被回答的问题 → 无条件 pass
   （reason=`repressed_unanswered_question`，18 个重申标记词 + 长度>10）。
   单独生效后 followup_pass 0.54 → 0.66（run e2e_verbose_20260711_105355），
   触发轮核对均为合理重申，无误伤；
2. ✅ **方向集合**（gold 侧）：`expected_followup_direction` 支持 `|` 分隔的多
   可接受方向，校验器取各备选最大匹配（先领域词命中、后语义 best-of）。
   增补脚本 scripts/apply_followup_direction_sets.py：29 处备选方向，措辞全部
   来自审计中实际观察到的合理客户行为，非任意放宽；
3. ⏸ **阈值校准**：0.50–0.60 扫描暂缓——方向集合落地后阈值边缘案例大多改由
   关键词命中，先看重跑结果再决定是否扫描；
4. ✅ **无 gold 兜底**：relevance 词池扩充领域词（适合/建议/选/条款/比例/配置等）。

**验收结果（2026-07-11，`--runs 3` 正式口径，全程未改生成侧代码）：**

| 指标 | 修缮前 | 修缮后（3 次运行区间） |
|---|---|---|
| followup_pass | 0.54 | **0.82–0.84**（mean 0.833） |
| dynamic_dialogue_pass | 0.46 | **0.68–0.70**（mean 0.693） |
| customer_retrieval_hit | 0.80 | 0.78–0.80（未动，下一批） |

- followup 未到 0.85 的残差（每次运行 ~7-8 轮）已逐条复核：全部属于
  "温度 0.7 客户走出 gold 未枚举的另一合理方向"的结构性残差。继续按单次
  采样加备选方向 = 追着噪声调 gold，违反"不为指标放宽评估"约定，**到此冻结**；
  0.82–0.84 是当前尺子的诚实下界（真实追问质量高于此值）。
- dynamic 未到 0.80 的瓶颈已不在 followup：被 customer_retrieval_hit
  （10 个 case 的 gold 证据/路由错配，见 §6）封顶。retrieval gold 修缮
  完成后 dynamic 预期可达 0.80+。

## 5b. 工单：customer_retrieval 尺子修缮（2026-07-11/12）

工作流与 §4/§5 完全相同（build_retrieval_audit → 判 verdict → 修数据/词表）。

**审计结论（11 条失败轮 / 10 case，trace e2e_verbose_20260711_124900）：
retrieval 1 条 / gold 9 条 / checker 1 条。**

- checker 1（e2e_001）：合规注意事项文档已在 rank-1，但 `合规` 同义词表用
  "监管/红线"类书面词，语料实际写"不实承诺/夸大/诱导/保监会"→ 词表已锚定语料；
- gold 9，三个子类：① 证据锚定理想脚本方向（同 followup 根因，5 条，
  scripts/apply_retrieval_evidence_sets.py 按审计实际方向增补，OR 语义）；
  ② `清晰说明` 为死类别——教学侧措辞在客户语料中零命中（2 条，已替换）；
  ③ FUND_GENERAL/INS_GENERAL 语料缺合规类文档（2 条，**语料建设 backlog**）；
- retrieval 1（e2e_037，**保留失败不修尺子**）：WM_ASSET 语料中 MCH_000154
  （费用结构：管理费 0.13-0.2%/手续费 0.15%）直接回答客户费用问题但未进
  top-5——真实召回缺陷，进检索改进 backlog（怀疑 keyword_recall 融合权重
  0.1 过低导致精确词面查询吃亏，属生成侧改动，须走门禁+re-baseline）。

**验收结果（2026-07-12，`--runs 3` 正式口径，零生成侧改动）：**

| 指标 | 修缮前 | 修缮后（3 次运行区间） |
|---|---|---|
| customer_retrieval_hit | 0.78–0.80 | **0.96–0.98**（mean 0.973） |
| dynamic_dialogue_pass | 0.68–0.70 | **0.76–0.86**（mean 0.813，达标 0.80） |
| followup_pass | 0.82–0.84 | 0.78–0.88（mean 0.833，同区间无回归） |

- 单次 verbose 复核（trace e2e_verbose_20260712_012302）：50 case 中检索仅
  1 条失败，即刻意保留的 e2e_037 真实召回缺陷（49/50=0.98）；e2e_001 由
  "不实承诺/保监会"同义词命中 rank-1 合规注意事项文档，其余审计轮均由
  实际方向证据命中。区间下沿 0.96 来自温度 0.7 下客户偶发走出证据集合的
  采样噪声，非系统性问题；
- 至此两把动态尺子（followup、customer_retrieval）修缮完毕，
  dynamic_dialogue_pass 反映真实链路质量。剩余失败集中在 followup 的
  结构性残差（见 §5 冻结说明）与 e2e_037。

## 5c. 工单：弱点标签 gold 穷举化（2026-07-12 执行中）

背景：scorer 套件的 `tag_micro_precision 0.21` 长期不可引用。审计确认主因是
**gold 大面积空标注**——50 case 中 29 条 `expected_weak_tags=[]`（原口径只标
"必需标签"），检测器报出的每个字面成立的标签都被记为 false positive；
`tag_pass 0.86` 虚高则因 expected 为空时直接判过。两个口径的矛盾同源。

工作流同 §4/§5/§5b：`eval_scorer --save-report` → `build_tag_audit.py`
（一行 = case×标签×fp/fn，附 transcript 摘录）→ 判 verdict → 改 gold。

早期初审得到 176 条差异；完成 provenance 和冻结 seed 改造后，当前审核清单为
**178 条 / 50 case**：fp 169 条暂分为 justified 140 / spurious 29，fn 9 条
暂分为 detector_miss 8 / gold_wrong 1。该分组是待逐条确认的 proposal，不能
直接作为正式 Gold。

- 候选判定口径写在 scripts/apply_tag_audit_verdicts.py docstring
  （共情不足按"客户有无情绪诉求+员工有无共情语"、逻辑结构不足与答非所问
  区分、红线类严格对照违规原话），供人工逐条审核；脚本只写
  `proposed_verdict`，不会自动批准 `verdict`；
- **检测器误报 backlog（36 条 spurious 的四个模式，保留失败不改 gold）**：
  ① 共情不足在中性问询/员工已共情的对话上滥报（16 条）；
  ② 行动引导不足在明确有引导（邀约/给资料/催签）时误报（5 条）；
  ③ 逻辑结构不足与"答非所问"混淆（6 条）；
  ④ 红线类偶发无据报出（合规问题/强推销/风险揭示不足等 9 条，含
  017/046 已有风险揭示仍报"风险揭示不足"）；
- 候选回灌结果当前标记为 `tag_status="pending"`，指标仅用于开发诊断；
  正式回灌由 scripts/apply_tag_gold_exhaustive.py 执行，要求每行均有
  `review_status="human_reviewed"`、reviewer 和有效 provenance，完成后才标记
  `tag_status="human_reviewed_exhaustive_v1"`。回灌只动 `expected_weak_tags`，不碰
  dialog_pairs/transcript_hash/分数带宽——冻结基线不受影响；
- 原始必需标签独立冻结在 `data/eval/scorer_tag_review_seed.jsonl`。audit 取
  “pending 候选与 seed 的差异”及“当前模型与 pending/seed 的新差异”并集，
  因此已经补入且本轮仍命中的候选也必须接受审核，不会被静默隐藏；
- 诚实代价预告：expected 变多后 `tag_pass`（全部 expected 须命中）会从
  0.86 回落，这是把虚高口径换成真实口径，不算回归。

待审核口径最新重跑结果：precision **0.8086**、recall **0.9235**、F1 **0.8622**、
exact match **0.30**。这组结果揭示了主要残差（尤其“共情不足”过报），但在
178 行完成复核前 `tag_metrics_citable=false`，不得作为正式基线引用。

审计安全约束：scorer report 必须是完整 LLM-only 运行，case 集合、transcript
integrity 和 tag Gold fingerprint 均需匹配；旧 report、subset、rule fallback、
被编辑或上下文变化的 audit 行都会被拒绝。score 基线则同时绑定 scorer config
fingerprint 和 score Gold fingerprint，任一变化都必须重新跑全量并 bless。

安全执行顺序：

```powershell
python -m eval.stages.eval_scorer --save-report data/eval/scorer_report_tags.json
python scripts/build_tag_audit.py
python scripts/apply_tag_audit_verdicts.py  # 只生成 proposal，不批准
python scripts/review_tag_audit.py --case-id <id> --tag <标签> --kind fp `
  --verdict justified --reviewer <姓名> --note <人工判定理由>
# 178 行全部显式审核后：
python scripts/apply_tag_gold_exhaustive.py
python -m eval.stages.eval_scorer --save-report data/eval/scorer_report_tags_v2.json
```

## 6. 当前已知边界（维持）

- PHONE_INVITATION 语料映射问题：留到下次 re-baseline 窗口（涉及 4+4 case
  的检索行为与带宽重审，transcript_hash 会随 scene 变更失效，属冻结后变更）；
- tag 指标当前仍不可正式引用：候选已补全，但 176 条差异尚待逐条审定；
  审定完成后的主战场是“共情不足”等过报标签去噪；
- Docker hash embedding 与 sentence-transformers 指标不可横向比较。
