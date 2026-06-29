# 意图标注评测集 Schema 与标注规范

## 目的

这份标注集是两个 P1 任务的共同地基：

1. **标定覆盖度阈值**：客户侧 intent gap、导师侧 must_point 覆盖度目前用的是经验阈值，需要人工 gold 标签来标定。
2. **训练 / 评测 BERT-mini 意图分类器**：作为 held-out 评测集 + 部分训练集，取代当前纯弱标签（弱标签来自关键词，会让 BERT 只学到关键词边界）。

## 产出文件

| 文件 | 说明 |
|---|---|
| `data/intent_eval_candidates.jsonl` | 抽样脚本生成的**待标注**候选（`gold_labels` 为空，`suggested_labels` 为关键词建议） |
| `data/intent_eval_gold.jsonl` | 人工标注完成后的 gold 文件（建议另存，不要覆盖候选文件） |

生成候选：

```powershell
.\.venv\Scripts\python.exe -m app.core.intent_eval_set_builder --target-size 250
```

## 字段定义

```jsonc
{
  "id": "IE_0001",                 // 稳定 ID
  "text": "提前取出来会不会有损失？", // 待标注语句（已清洗）
  "channel": "customer",           // customer=客户话 / employee=员工话
  "scene_id": "INS_PERIODIC",      // 来源场景，可为 null
  "source": "customer_profiles.opening_question", // 溯源
  "suggested_labels": ["liquidity_concern"],      // 关键词建议（仅参考，可能错）
  "gold_labels": [],               // ★人工填写★ 多标签，可为空
  "needs_review": true             // 标注完成后置 false
}
```

## 标注规范

### 标签集（多标签，可 0~多个）

| 标签 | 含义 | 典型表达 |
|---|---|---|
| `rate_concern` | 利率/收益/同业比较/是否划算 | "收益太低了吧""别的银行更高" |
| `liquidity_concern` | 提前支取/临时用钱/期限灵活性 | "急用钱能取吗""期限太长" |
| `safety_concern` | 本金安全/风险/亏损/保障 | "会不会亏""本金安全吗" |
| `procedure_question` | 办理流程/材料/查询/下一步 | "怎么办理""要带什么" |
| `rejection_or_hesitation` | 犹豫/拒绝/再考虑/和家人商量 | "再想想""回去商量" |
| `compliance_sensitive` | 保证/承诺/最高/稳赚等合规敏感 | "能保证吗""稳赚不亏" |

### 标注原则

1. **按语义判断，不按关键词**——`suggested_labels` 只是起点，经常会漏标或误标，以实际语义为准。
2. **多标签**：一句话可同时属于多个意图（如"收益低又怕亏"= `rate_concern` + `safety_concern`）。
3. **空标签合法**：寒暄、过渡、与六类都无关的句子，`gold_labels` 留空 `[]`。这类负样本对标定阈值很重要，别丢。
4. **compliance_sensitive 看表达不看角色**：无论客户诱导还是员工说出"保证/稳赚"，只要出现合规敏感表达就打这个标签。
5. **channel 不影响标签**：意图标签对客户话和员工话通用（员工"我说明一下利率"也属于 `rate_concern` 话题）。
6. 标完一条把 `needs_review` 置 `false`。

### 规模建议

- 首批 250 条，覆盖 6 类各 ≥ 20 条正样本 + 一定比例空标签负样本。
- 标注后按 ~70/30 切分训练/评测，评测集不参与训练。

## 下游用法

- **覆盖度标定**：用 gold 标签反推 intent 覆盖阈值（当前 0.05 偏松）和 must_point 阈值（当前 0.40）。
- **BERT-mini**：gold 训练集喂 `bert_mini_trainer`，gold 评测集报 micro/macro F1，对比 keyword baseline。
