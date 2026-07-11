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

**审计结论（29 条失败轮，AI 辅助判定 + 人工抽检）：
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

## 6. 当前已知边界（维持）

- PHONE_INVITATION 语料映射问题：留到下次 re-baseline 窗口（涉及 4+4 case
  的检索行为与带宽重审，transcript_hash 会随 scene 变更失效，属冻结后变更）；
- tag_micro_precision（~0.22）不可引用：gold 只标必需标签非穷举；
  标签去噪是评估修缮完成后的主战场；
- Docker hash embedding 与 sentence-transformers 指标不可横向比较。
