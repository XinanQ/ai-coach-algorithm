# 算法文档 03 — LLM 客户模拟

> 涉及代码:[app/core/llm_customer.py](../../app/core/llm_customer.py) + [app/core/llm/prompts/customer.py](../../app/core/llm/prompts/customer.py) + [app/core/dialog_manager.py:_next_customer_question](../../app/core/dialog_manager.py)

## 1. 核心问题

陪练系统的对方不是真人,需要 AI 扮演客户与员工对话。这里有三个层次的挑战:

| 挑战 | 老方案的问题 | 我们的解法 |
|---|---|---|
| **生成内容** | 写死的话术模板,每次答员工同样的话就触发同一句追问 | LLM 根据完整上下文生成 |
| **角色稳定** | LLM 容易出戏("作为 AI 我不能..." / "您好,请问需要什么帮助") | L1 人设 + L4 边界硬约束 |
| **合理追问** | 纯 LLM 不知道哪些客户顾虑还没被回应,容易瞎问 | **算法识别 gap → 喂给 LLM 作为辅助信号** |

**核心设计:算法做识别,LLM 做生成。算法的 gap 检测和 RAG 检索作为"提示信号"喂给 LLM,LLM 综合上下文自然生成客户追问。**

## 2. 整体数据流

```
dialog_manager.reply_dialogue
        │
        ├─ analyze_customer_answer(employee_message) → intent_scores
        ├─ update_covered_intents → covered_intents(跨轮累积)
        ├─ compute_intent_gap(expected, covered) → gap_intents   ← 算法识别
        ├─ retrieve_marketing_knowledge(route="customer", focus_intents=gap)
        │       ↓                                                 ← 算法检索
        │   retrieval_items
        │
        └─ _next_customer_question  ← reply 阶段唯一的 LLM 调用(评分已下线)
                                          │
                                          ↓
                _next_customer_question (LLM-first)
                          │
              ┌───────────┴────────────┐
              │ AI_COACH_CUSTOMER_LLM=? │
              └───────────┬────────────┘
                  llm     │     template
                  ↓                ↓
        generate_customer_question_with_llm
                │
                ├─ get_customer_profile(scene_id) → 画像
                ├─ get_customer_builder_for_scene(profile, scene_id)
                │        ↓
                │   6 层 prompt:
                │     L1 客户角色框架(静态)
                │     L3 决策树指令(静态)
                │     L4 全局边界 + 客户专属边界(静态)
                │     L5 输出形态(静态)
                │     L2-Anchor 客户画像(静态,scene-stable,**per-scene 缓存**)
                │     L2 历史+员工话+gap+检索(动态,每轮重渲染)
                │
                └─ _call_llm_text(method="customer", scene_id)
                          ↓
                   AsyncOpenAI → DeepSeek
                          ↓
                   clean_plain_text(text) → 去除引号包裹等噪声
                          ↓
                   返回客户追问字符串
                          │
                  ┌───────┴───────┐
                  │ LLM 成功?     │
                  └───────┬───────┘
                       yes│   no
                          ▼            ▼
                    用 LLM 输出    CUSTOMER_INTENT_PROBES 模板兜底
```

## 3. 算法辅助 LLM 的 4 类信号

LLM prompt 的 L2 上下文层会拿到 4 类算法辅助信号,让 LLM 不需要"凭空想客户该问什么":

### 3.1 客户画像(`customer_profile_loader.get_customer_profile`)

共 **39 个客户画像**,覆盖全部 **14 个场景**,每场景 2-3 个难度等级(低/中/高)。

```json
{
  "customer_id": "CUST_LIQUIDITY_PERIODIC",
  "customer_type": "流动性担忧型",
  "personality": "谨慎,担心钱被长期锁定,反复确认中途能不能取",
  "concern": "缴费期限太长、每年续缴压力、中途退保损失",
  "expected_intents": ["liquidity_concern", "procedure_question"],
  "difficulty_level": "中"
}
```

画像选择支持**自适应难度**(`adaptive_difficulty.py`):用户连续高分自动升难度(选"高"画像),连续低分自动降(选"低"画像)。也可通过 `start_dialogue(difficulty="高")` 手动指定。

完整画像覆盖见 [06_memory_and_adaptive.md §6](06_memory_and_adaptive.md)。

注入到 **L2-Anchor 客户画像**(`CustomerSceneAnchorLayer`,**静态层**,**per-scene 一份**)。

**关键设计:画像不进动态 L2,而是在 builder 构造时烤进静态 L2-Anchor 层**。

| | 旧设计 | 新设计 |
|---|---|---|
| 画像位置 | L2.1 动态,每次重渲染 | L2-Anchor 静态,builder 构造时锁定 |
| 跨调用共享 | 同 session 内字符串相同(但 Python 重建对象) | 同 scene 所有调用字节完全一致 |
| DeepSeek cache 命中 | 不稳定 | 稳定(SceneAnchor 进入静态前缀) |
| 改画像生效 | 立即(只是重渲染) | 需要重启服务(builder 缓存) |

LLM 通过 personality 字段保持角色一致性——同一个 session 内每次发言都看到同样的人设。详细缓存机制见 [05_prompt_architecture.md §4.6](05_prompt_architecture.md)。

### 3.2 对话历史(`session.messages`)

最近 6 轮对话(交替 ai_customer / employee),让 LLM 知道:
- 自己之前问过什么(避免重复)
- 员工之前怎么回答的(可针对性追问)

注入到 **L2.1**(动态层,profile 已经移到 L2-Anchor 后,L2 编号往前提)。角色重命名为 `客户(你之前说的)` / `员工`,提示 LLM "之前那些是你说的"。

### 3.3 算法 gap 分析(关键信号)

```json
{
  "gap_intents": ["procedure_question"],
  "covered_intents": ["liquidity_concern", "rate_concern"]
}
```

注入到 **L2.3**(动态层):

```
## L2.3 算法辅助分析(参考,但要看上下文综合判断)
- 你尚未被回应的顾虑(按重要性排序): procedure_question(办理流程、材料、查询、下一步动作)
- 你已经被回应过的顾虑: liquidity_concern(...)、rate_concern(...)
```

**注意措辞**:用"参考,但要看上下文综合判断",**不强制** LLM 必须追问 gap 里的话题。这是因为:
- 算法的意图识别(关键词)可能不准——员工实际说了但 keyword 没匹配
- LLM 读对话上下文能做更准的判断
- gap 只是"提示信号",不是"硬约束"

### 3.4 客户侧 RAG 检索结果

```
## L2.4 相关的标准客户话术(参考语气,严禁照抄)
1. 客户:我怕中途要用钱,这个能取出来吗?
2. 客户:那如果我交不上了,前面的钱不就白交了?
```

注入到 **L2.4**(动态层)。注意**"严禁照抄"**——RAG 检索是给 LLM "看真客户怎么说",不是让它复读标准话术。LLM 学语气,不学具体句子。

## 4. 5 层 Prompt 设计

详细架构见 [05_prompt_architecture.md](05_prompt_architecture.md)。客户场景的 5 层简要:

| 层 | 内容(关键点) |
|---|---|
| L1 系统人设 | "你是金融营销陪练的客户。最高准则:保持身份不出戏 / 像真客户那样质疑挑刺 / 不帮员工想答案" |
| L3 核心指令 | **决策树**:① 合规风险优先质问 → ② 否则追问 gap 第一个顾虑 → ③ 否则推进办理意向 → ④ 紧扣员工本轮话不跑题 |
| L4 全局边界 | 反幻觉、反内部矛盾、禁多余文字 |
| L4 客户专属边界 | **禁暴露 AI 身份** / **禁 AI 腔过渡词** / **禁重复之前句式** / **禁帮员工想答案** / **禁前后缀** |
| L5 输出形态 | 一到两句话 / ≤60 字 / 中文口语化 |
| **L2-Anchor 客户画像** | **scene-stable 静态层**,builder 构造时锁定 profile(per-scene 缓存) |
| L2 动态上下文 | 历史 + 员工本轮话 + gap + 检索(画像已移到 L2-Anchor) |

## 5. 决策树:LLM 的 4 步判断

L3 instruction 强制 LLM 按这个优先级决策(在心里走一遍,不输出过程):

```
1. 员工话有合规风险(承诺/保证/绝对化/包装成存款/合理避税)?
   yes → 优先尖锐质问,逼员工把承诺具体化
   no  → 进 2

2. 有未回应顾虑(gap 列表非空)?
   yes → 围绕第一个未回应顾虑发问,可带情绪
   no  → 进 3

3. 全部已回应?
   yes → 表示理解,自然推进到办理意向

4. 任何情况下:紧扣员工本轮具体说的话,不跑题
```

**为什么把"合规风险"放最优先**:因为合规违规是这个产品的核心训练价值。员工说"稳赚",AI 客户必须当场质问"稳赚?你写进合同里我立刻办",这样员工才能真切感受到"这话不能说"。

## 6. 模板兜底(`CUSTOMER_INTENT_PROBES`)

当 LLM 不可用时(无 KEY / 调用失败 / `AI_COACH_CUSTOMER_LLM=template`),回退到 6 句固定模板:

```python
CUSTOMER_INTENT_PROBES = {
    "rate_concern": "那收益到底有多少?我感觉还是偏低,跟理财、存款比有什么优势?",
    "liquidity_concern": "那我万一中途要用钱、或者交不上了,能取出来吗?会不会亏?",
    "safety_concern": "那本金到底安不安全?万一亏了、或者公司出问题了怎么办?",
    "procedure_question": "那具体怎么办、要带什么材料、下一步我该做什么?",
    "rejection_or_hesitation": "我还是有点犹豫,你说的这些我得再想想,为什么我现在就得办?",
    "compliance_sensitive": "你刚才说的这个能不能给我保证?写进合同里吗,达不到怎么办?",
}
```

兜底决策(`dialog_manager._next_customer_question`):

```python
1. 员工话命中 compliance_sensitive intent → 用 compliance_sensitive 模板
2. 按 gap_intents 顺序找第一个有模板的 → 用对应模板
3. 全覆盖时 → "你说的这些我大概明白了,那我现在适合办吗?需要怎么弄?"
```

**模板的局限**:同一个 gap 永远是同一句话。员工反复跟同一个 gap 周旋时,客户会反复说同一句,显得很傻。所以默认走 LLM 路径,模板只作兜底。

## 7. 输出清洗(`parser.clean_plain_text`)

LLM 有时会无视"不要前后缀"的要求,加引号或标记:

```
"那我万一中途要用钱呢?"
「那我万一中途要用钱呢?」
客户:那我万一中途要用钱呢?
```

`clean_plain_text` 去除常见包裹符:`" ' 「 」 『 』` + 首尾空白。这是最后一道净化。

## 8. 调优入口速查

| 想改什么 | 改哪里 |
|---|---|
| 客户角色框架(L1) | `app/core/llm/prompts/customer.py` `CustomerPersonaLayer` |
| 决策树优先级(L3) | `app/core/llm/prompts/customer.py` `CustomerInstructionLayer` |
| 客户专属硬约束(L4) | `app/core/llm/prompts/boundaries.py` `CustomerBoundaryLayer` |
| 输出形态(L5) | `app/core/llm/prompts/formats.py` `CustomerFormatLayer` |
| 上下文渲染(L2) | `app/core/llm/prompts/customer.py` `CustomerContextLayer.render` |
| 历史显示轮数(默认 6) | `customer.py:_format_history(limit=6)` |
| RAG 显示条数(默认 2) | `customer.py:_format_retrieval(limit=2)` |
| LLM temperature(默认 0.7) | `llm_scorer._call_llm_text(temperature=0.7)` |
| 模板话术 | `dialog_manager.CUSTOMER_INTENT_PROBES` |
| 全覆盖时的收尾话术 | `dialog_manager._next_customer_question` 末尾 |
| 切换 LLM/Template | `AI_COACH_CUSTOMER_LLM=llm|template` 环境变量 |
| 客户画像 | `data/customer_profiles.json` |

## 9. 已知限制与待办

| 问题 | 现状 | 路径 |
|---|---|---|
| LLM 偶尔出戏("作为客户我..." 这种 meta 表述) | L4 已禁,~99% 抓住 | 出戏时重新生成(目前无重试) |
| ~~仅 4 个画像,缺多样性~~ | ✅ 已解决:39 个画像,14 场景全覆盖 | — |
| ~~客户语气固定~~ | ✅ 已解决:低/中/高三档难度,语气从友善到极端难缠 | — |
| 客户追问无 retry(LLM 失败直接走模板) | 设计 | 模板兜底已够鲁棒,暂不加 retry |
| 不显式验证客户身份没出戏(无 Pydantic) | 已知 | LLMCustomerOutput 已定义但当前不强制 |

## 10. 失败回退矩阵

| 失败点 | 兜底 | 客户体验 |
|---|---|---|
| 无 `DEEPSEEK_API_KEY` | 模板查表 | 同一 gap 永远同一句话,但能跑通 |
| LLM 网络超时 / 5xx | retry 3 次(同 scorer),失败后模板 | 延迟变长后兜底,体验略差 |
| LLM 429 限流 | 退避重试,失败后模板 | 同上 |
| LLM 输出空字符串 / 失败 | 模板 | 同 "无 KEY" 情况 |
| LLM 出戏(在生成的话里说"作为AI") | **当前无检测**,会直接输出 | 演示风险,需要时加 post-check |
| `clean_plain_text` 清掉所有内容 | 返回 None → 模板 | 模板兜底 |

## 11. 演示亮点

跑一个 INS_PERIODIC 场景对话,重点观察 4 种情景:

| 情景 | LLM 客户的表现(对比模板) |
|---|---|
| 员工答得很普通 | LLM 会**揪你刚说的具体词**反问(如"你光说以合同为准,那合同里到底...") |
| 员工补充信息 | LLM 沿着新信息继续追问,**不会重复上一句**(模板会) |
| 员工踩合规雷 | LLM 当场质问,**精准锁定最严重的违规**(如"跟存款一样"),而不是泛泛 |
| 员工挽救纠错 | LLM **语气缓和**,推进到下一话题(模板做不到) |

`/metrics/llm` 里看 `method=customer` 那一行,能看到 LLM 客户每次调用的 tokens/latency,证明 LLM 真在工作。
