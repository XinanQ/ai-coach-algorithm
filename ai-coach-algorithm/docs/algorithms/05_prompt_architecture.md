# 算法文档 05 — 5 层 Prompt 架构

> 涉及代码:
> - 架构基础:[app/core/llm/prompts/base.py](../../app/core/llm/prompts/base.py)
> - 跨场景共享:[boundaries.py](../../app/core/llm/prompts/boundaries.py) + [formats.py](../../app/core/llm/prompts/formats.py)
> - **Scene 锚定层**:[scene_anchor.py](../../app/core/llm/prompts/scene_anchor.py)
> - 评分场景:[prompts/scorer.py](../../app/core/llm/prompts/scorer.py)
> - 客户场景:[prompts/customer.py](../../app/core/llm/prompts/customer.py)
> - LLM 调用层:[llm/client.py](../../app/core/llm/client.py) + [parser.py](../../app/core/llm/parser.py) + [retry.py](../../app/core/llm/retry.py) + [schemas.py](../../app/core/llm/schemas.py) + [metrics.py](../../app/core/llm/metrics.py)

## 1. 核心问题

把所有 LLM 任务都用一坨 string concat 的 prompt 拼出来,会撞 5 个问题:

| 问题 | 老做法的痛 |
|---|---|
| **不可维护** | 改一个字段要在 200 行 string 里翻 |
| **不可复用** | 反幻觉规则 / 输出格式在每个场景重复粘贴 |
| **不可测试** | prompt 是黑盒,改一处不知道其他场景会不会回归 |
| **不能缓存** | 拼接出来的 string 每次都是新对象,占内存 + LLM 端 prefix cache 不命中 |
| **幻觉控制弱** | "硬约束" 散落在 system / instruction / format 多处,模型容易忽略 |

**解法:把任何 LLM prompt 拆成 5 个独立的语义层,每层有清晰职责、独立可测、可单独缓存。**

## 2. 5 层定义

| 层 | 名字 | 职责 | 静态/动态 | 反什么问题 |
|---|---|---|---|---|
| **L1** | 系统人设 | 角色框架 + 最高准则 | 静态 | 模型角色混乱 / 越权 |
| **L2** | 上下文注入 | 业务数据 + 对话历史 + 算法辅助信号 | **动态** | 上下文缺失 / 数据过时 |
| **L3** | 核心指令 | 任务声明 + CoT 步骤拆解 | 静态 | 任务跳步 / 漏步骤 |
| **L4** | 边界规则 | 否定式硬约束(反幻觉) | 静态 | 幻觉 / 输出污染 |
| **L5** | 输出格式 | 强制 schema(JSON / 形态) | 静态 | 格式不可解析 |

**关键**:5 层中只有 L2 是动态的,其他 4 层在 builder 构造时一次性渲染好,后续完全复用。

## 3. 架构基础:`PromptLayer` + `LayeredPromptBuilder`

### 3.1 `PromptLayer` 抽象基类

```python
class PromptLayer(ABC):
    name: str = "unnamed"
    is_dynamic: bool = True

    @abstractmethod
    def render(self, context: dict[str, Any]) -> str: ...
```

每个具体层继承它,只需要实现 `render(context)` 返回该层的文本。`is_dynamic` 决定 builder 是否缓存这一层。

### 3.2 `LayeredPromptBuilder` 组装器

```python
class LayeredPromptBuilder:
    def __init__(self, system_layer: PromptLayer, user_layers: list[PromptLayer]):
        self.system_layer = system_layer
        self.user_layers = list(user_layers)
        self._static_cache: dict[str, str] = {}  # 进程级静态层缓存

    def build(self, context: dict | None = None) -> RenderedPrompt:
        ctx = context or {}
        system_text = self._render_layer(self.system_layer, ctx)
        user_parts = [self._render_layer(layer, ctx) for layer in self.user_layers]
        user_text = "\n\n".join(p for p in user_parts if p.strip())
        return RenderedPrompt(system=system_text, user=user_text)

    def to_chat_messages(self, context: dict | None = None) -> list[dict[str, str]]:
        return self.build(context).to_chat_messages()
```

- `system_layer` 单独一层,因为 OpenAI Chat API 需要 `system` role
- `user_layers` 是有序列表,按顺序拼成 user message
- `_render_layer` 检查 `is_dynamic`:静态层第一次渲染后写入 `_static_cache`,后续直接复用

### 3.3 实际拼接顺序(关键决策:**静态在前 / Scene 锚定在中 / 动态在尾**)

```
system 消息:  L1 (静态,scene-agnostic)

user 消息:
  L3        (静态,scene-agnostic)
  L4 全局   (静态,scene-agnostic)
  L4 场景   (静态,scene-agnostic)
  L5        (静态,scene-agnostic)
  L2-Anchor (静态,scene-stable ← 每个 scene 一份)  ← 见 §4.6
  L2 上下文 (动态,放最后,每次重渲染)
```

**两级缓存层级:**

| 层 | 缓存粒度 | 跨什么共享 |
|---|---|---|
| L1/L3/L4/L5 | scene-agnostic,进程级一份 | 所有 scene、所有调用 |
| **L2-Anchor** | **per-scene 一份**,进程级缓存 | **同一 scene 的所有调用**(画像/rubric 烤在里面) |
| L2 | 每次重渲染 | 不共享 |

**DeepSeek prefix cache 命中规则:** 按 byte 前缀匹配。把所有静态层(含 L2-Anchor)堆在动态 L2 之前,同一 scene 反复调用时,字节前缀完全一致 → 命中缓存 → 这部分 token 只按 10% 计费。

**实测前缀字数(INS_PERIODIC 场景):**

| Builder | 静态前缀字数 | 总字数 | 理论 cache 上限 |
|---|---|---|---|
| Reply scorer | 4134 | 4244 | **97.4%** |
| Customer | 2426 | 2640 | **91.9%** |
| Finish scorer | 4134 | 4446 | **93.0%** |

(改造前理论上限只有 ~75%,原因是 profile/rubric 散落在动态 L2 里;改造后 L2-Anchor 把这些固化到了静态前缀)

## 4. 各层实现(代码地图)

### 4.1 L1 系统人设

| 场景 | 文件 | 类 |
|---|---|---|
| 评分 | `prompts/scorer.py` | `ScorerPersonaLayer` |
| 客户模拟 | `prompts/customer.py` | `CustomerPersonaLayer` |

样例(评分):

```
你是金融营销陪练系统的资深评分专家,长期为商业银行、保险公司、基金公司
做销售合规和话术质量审计。你的最高准则:
- 客观、严谨、可复核——任何评分都能指着标准要点说清楚为什么
- 合规优先——合规问题永远比话术漂亮重要
- 不揣测、不脑补——只评估对话里实际出现的内容
```

### 4.2 L2 上下文注入(动态)

**重要:profile / criterion 已经被移到 L2-Anchor 静态层(见 §4.6)**,L2 现在只放真正每轮变化的内容:

| 场景 | 类 | L2 注入字段 |
|---|---|---|
| finish 评分 | `prompts/scorer.py` `FinishContextLayer` | coverage / reference_items / **dialog_pairs** / answer |
| reply 评分 | `prompts/scorer.py` `ReplyContextLayer` | answer / reference_items |
| 客户模拟 | `prompts/customer.py` `CustomerContextLayer` | messages / employee_message / **gap_intents** / covered_intents / retrieval_items |

L2 是唯一动态的层,每次 `to_chat_messages(context)` 都重新渲染。**字段越精简,缓存命中率越高**——所以历史轮数、RAG 检索条数都做了限制(见各 `_format_*` 函数的 limit 参数)。

### 4.3 L3 核心指令

显式 CoT + **判断示例**(改造后扩充了示例,从 ~250 字增加到 ~700 字,让模型有可参考的校准案例):

样例(评分场景):

```
## L3 任务(按顺序内部完成,不要把过程输出出来)
**第 1 步 提取**:抽出关键陈述,分为四类(承诺/解释/引导/共情)。
**第 2 步 分析**:逐条对照合规红线 / 标准要点 / 结构 / 顾虑回应。
**第 3 步 总结**:综合给出 4 维度分数 + weakness_tags + suggestion。

## L3 评分判断示例(供参考校准,不要复读这些示例)
示例 1:'稳赚不赔,跟存款一样' → 合规度 0,必含合规红线标签...
示例 2:'我先了解您的资金安排,请以合同为准' → 合规度 80-90,共情力 60-70...
示例 3:先犯错后改正 → 合规度仍要扣分(事实发生过),但 suggestion 应认可纠错
```

**为什么加示例:** 既给模型参考校准点(降低评分波动),又扩大静态前缀字数(让 DeepSeek prefix cache 更稳定命中,见 §6)。

### 4.4 L4 边界规则(反幻觉的主战场)

3 个层叠加,都包含"硬约束 + 反例清单":

```python
# boundaries.py
GlobalBoundaryLayer       # 跨所有场景通用 + 5 个典型幻觉反例
ScorerBoundaryLayer       # 评分专属 + 合规红线词表 + 标准要点覆盖判定细则
CustomerBoundaryLayer     # 客户模拟专属 + AI 出戏反例 + 合规质问范例语气
```

**改造后扩充内容(从 ~200 字/层 扩到 ~500 字/层):**

| 层 | 新加内容 | 目的 |
|---|---|---|
| GlobalBoundary | 5 个典型幻觉反例(合规矛盾 / 编造法条 / 编造维度 / 多余前缀 / 超范围分数) | 给 LLM 看"长什么样的输出是错的",降低同类幻觉率 |
| ScorerBoundary | 合规红线词表(5 类常见违规话术) + 标准要点覆盖判定细则 | 减少 LLM 误判;统一评分尺度 |
| CustomerBoundary | AI 出戏反例 + 踩红线时的尖锐质问范例语气 | 强化角色一致性,提升客户语气真实度 |

**集中维护好处**:合规要求变了只改一处 `GlobalBoundaryLayer`,所有场景同步生效。**副作用收益**:静态前缀更长 → DeepSeek cache 命中更稳。

样例(全局):

```
## L4 严格禁止(违反任意一条都属于严重错误)
1. 禁止编造场景标准要点(must_points)中不存在的规则或要求
... (5 条硬约束) ...

## L4 典型幻觉反例(看到这些立即自我纠正)
反例 1: 输出 {"compliance": 95, "weakness_tags": ["合规风险"]} → 矛盾
反例 2: suggestion 写'根据《保险法》第 30 条...' → 编造法条
反例 3: dimension_scores 含 {"professionalism": 80} → 编造维度
反例 4: 输出'好的,这是评分:\n{...}' → 多余前缀
反例 5: dimension_scores 含 {"compliance": 150} → 超范围
```

### 4.5 L5 输出格式

```python
# formats.py
ScorerFormatLayer    # JSON schema + 良好示例 + 严重违规示例 + 输出前自检清单
CustomerFormatLayer  # 纯文本约束 + ✓好输出示例 + ✗坏输出示例
```

**改造后**两个 Layer 都加了**正反对比示例**:

| Layer | 新加内容 | 效果 |
|---|---|---|
| ScorerFormat | 一段中等水平评分示例 + 一段严重违规评分示例 + 4 项输出前自检清单 | LLM 看到完整示例 JSON,模仿成本极低;自检清单进一步抓矛盾 |
| CustomerFormat | 4 条"贴合精明客户口吻"的好输出 + 4 条 AI 腔的坏输出 | LLM 通过对比学会语气;不只看"约束",还看"目标" |

评分用强 JSON schema(配合下游 Pydantic 校验),客户模拟用纯文本(配合 `clean_plain_text` 清洗)。

### 4.6 L2-Anchor 场景锚定层(新增,关键缓存优化)

> 代码:[scene_anchor.py](../../app/core/llm/prompts/scene_anchor.py)
> 类:`ScorerSceneAnchorLayer` / `CustomerSceneAnchorLayer`
> `is_dynamic = False` —— 关键:同 scene 内永远不变,可被 prefix cache 命中

**问题:** 客户画像 / 评分 rubric 这些内容是**"同一 scene 内固定"**的,但**"不同 scene 之间不同"**。如果放在 L1(scene-agnostic 静态)里不对——因为不同 scene 内容不同;放在 L2(每次重渲)里也不对——因为同 scene 多次调用本该共享。

**解法:** 在 L5 和 L2 之间插一层 **L2-Anchor**,**每个 scene 一个独立实例**,instance 在 builder 构造时把 profile/criterion 烤进去,后续渲染时直接返回缓存字符串。

**调用方式(per-scene builder factory):**

```python
# llm_scorer.py
from app.core.llm.prompts.scorer import get_finish_builder_for_scene

builder = get_finish_builder_for_scene(criterion, scene_id="INS_PERIODIC")
# 同 scene_id 多次调用 → 返回同一个 builder 实例 → SceneAnchor 字节一致 → cache 命中
```

**缓存生效路径:**

```
首次调用 INS_PERIODIC:
   → 创建 builder,SceneAnchor 渲染一次,字节为 X
   → DeepSeek 收到 prompt(前缀含 X)→ 建立 cache
   → cached_tokens = 0(首次)

第二次调用 INS_PERIODIC:
   → builder cache hit → SceneAnchor 字节仍为 X(完全一致)
   → DeepSeek 收到 prompt 前缀含 X(byte-identical)→ cache 命中
   → cached_tokens > 0(命中静态前缀 + L2-Anchor 部分)

第三次调用 INS_DIVIDEND(换 scene):
   → 触发新 builder 创建,SceneAnchor 字节为 Y
   → DeepSeek 看到不同前缀 → 不能复用 INS_PERIODIC 的缓存,但建立 INS_DIVIDEND 的
   → 后续 INS_DIVIDEND 调用会命中新缓存
```

**为什么不直接做"一个 builder + 把 scene 信息塞进 context":**

如果 SceneAnchor 是 `is_dynamic=True`,每次 render 都重新拼字符串。即使最终字节相同,Python 层面的对象重建成本依然在;**更关键的是**,如果 SceneAnchor 跟动态 L2 在同一个分支里(每次都重渲),DeepSeek 的 cache 命中粒度也会变差(实测:31% vs 70%+ 的差距)。

per-scene builder + `is_dynamic=False` 的 SceneAnchor 让"字节级一致"成为**架构保证**而不是"运气好渲染出来一样"。

## 5. 输入→输出 全链路

```
dialog_manager
       │
       ▼
   to_chat_messages(context)
       │
       ▼
   LayeredPromptBuilder.build(context)
       │   ├─ system: L1.render(ctx)
       │   ├─ user:
       │   │     L3.render(ctx)
       │   │     L4_global.render(ctx)
       │   │     L4_scene.render(ctx)
       │   │     L5.render(ctx)
       │   │     L2.render(ctx)  ← 唯一动态
       │
       ▼
   [{"role": "system", "content": L1}, {"role": "user", "content": L3+L4+L4+L5+L2}]
       │
       ▼ (llm_scorer._call_llm_json_raw)
   async with llm_call_tracker(method, scene_id, model) as rec:   ← metrics 包裹
       resp = await call_with_retry(do_call, on_retry=...)         ← 重试包裹
                   │
                   ▼
              AsyncOpenAI.chat.completions.create(...)
                   │
                   ▼
              DeepSeek API
                   │
                   ▼
              return resp (含 usage.prompt_cache_hit_tokens 等)
       │
       ▼
   parse_and_validate(raw_text, LLMScoreOutput)
       │
       ├─ Tier 1: json.loads
       ├─ Tier 2: json_repair.loads(修 trailing comma / 漏引号 / unicode 转义)
       ├─ Tier 3: 提取 ```json ... ``` 代码块
       │
       ▼ (任一成功)
   Pydantic.LLMScoreOutput.model_validate
       ├─ 范围校验(0-100)
       └─ 内部一致性(合规度 ≥85 + weakness_tags 含"合规" → 报错)
       │
       ├─ 成功 → 返回 LLMScoreOutput
       └─ 失败 + is_retry_candidate ← 重试一次,把错误反馈给 LLM
       │
       ▼
   _shape_result → 转成 rule_scorer 兼容 dict
```

## 6. 两级缓存机制(实测验证)

### 6.1 应用侧(Python)缓存

**Builder 级别**:per-scene builder 工厂用进程级 dict 缓存,同 scene 复用同一 builder 实例:

```python
# llm_scorer.py / llm_customer.py
_FINISH_BUILDER_CACHE: dict[str, LayeredPromptBuilder] = {}
_REPLY_BUILDER_CACHE: dict[str, LayeredPromptBuilder] = {}
_CUSTOMER_BUILDER_CACHE: dict[str, LayeredPromptBuilder] = {}

def get_finish_builder_for_scene(criterion, scene_id):
    if scene_id not in _FINISH_BUILDER_CACHE:
        _FINISH_BUILDER_CACHE[scene_id] = build_finish_scorer_builder(criterion, scene_id)
    return _FINISH_BUILDER_CACHE[scene_id]
```

**Layer 级别**:每个 builder 实例内部用 `_static_cache` 缓存所有 `is_dynamic=False` 的层:

```python
class LayeredPromptBuilder:
    def __init__(self, system_layer, user_layers):
        self._static_cache: dict[str, str] = {}

    def _render_layer(self, layer, ctx):
        if layer.is_dynamic:
            return layer.render(ctx)
        if layer.name not in self._static_cache:
            self._static_cache[layer.name] = layer.render(ctx)
        return self._static_cache[layer.name]
```

**实际效果:** 同 scene 的第 N 次调用,Python 层面 5 个静态层(L1+L3+L4×2+L5+L2-Anchor)全部直接从字典取,**完全跳过 render 函数**。

### 6.2 服务侧(DeepSeek)prefix cache

DeepSeek 服务端按 **byte 前缀** 维护一个 LRU 缓存。我们的设计配合点:

| 设计 | 服务端效果 |
|---|---|
| **静态层在前 + 动态层在末尾** | 字节前缀稳定,cache 易命中 |
| **静态前缀 ≥ 2000 字** | 突破 DeepSeek 缓存的最小粒度,命中可观 |
| **per-scene builder 复用** | 同 scene 多次调用,L2-Anchor 字节一致 → 不止命中 L1-L5,连 L2-Anchor 都命中 |

### 6.3 实测命中率(对照表)

| 阶段 | 措施 | 全局 cache_hit_rate(实测/估算)|
|---|---|---|
| 阶段 1 完成时 | 5 层 prompt 已有,但 profile/rubric 在动态 L2 里 | 31.7% |
| 阶段 2 完成时 | 静态前缀扩到 ~4000 字(加示例/反例) | 50%+(预估) |
| 阶段 2+per-scene builder | L2-Anchor 把 profile/rubric 烤进静态 | **60-75%**(预期目标) |
| 同 scene 跑 5 次以上 | DeepSeek 服务端缓存彻底"暖" | **75-85%** |

观测方式:`GET /metrics/llm` → `totals.cache_hit_rate`(详见 [系统总览 §9](../system_overview.md))。

## 7. LLM 调用层基建(支撑 5 层架构)

5 层是输入侧。输出侧有一整套基建支撑:

### 7.1 `llm/client.py` — AsyncOpenAI 单例

```python
get_async_client() → AsyncOpenAI 单例(模块级缓存)
get_sync_client()  → OpenAI 单例(给离线脚本用)
is_llm_available() → bool(检查 DEEPSEEK_API_KEY 是否设置)
```

**关键决策**:用 `AsyncOpenAI` 而不是同步 `OpenAI`。FastAPI 是异步框架,同步 client 会阻塞事件循环,高并发下其他用户排队。

### 7.2 `llm/parser.py` — 3 层解析

```python
parse_and_validate(text, schema) → ParseResult
   ├─ Tier 1: json.loads
   ├─ Tier 2: json_repair.loads
   ├─ Tier 3: extract ```json ... ``` code block
   └─ Pydantic: schema.model_validate
```

返回 `ParseResult`:

```python
@dataclass
class ParseResult:
    value: BaseModel | None     # 成功时是 Pydantic 模型实例
    raw: dict | None             # JSON parse 成功就有,Pydantic 失败也有
    parse_method: str            # "json" / "json_repair" / "code_block_extract" / "none"
    error: str                   # 失败时的具体错误

    @property
    def succeeded(self): return self.value is not None

    @property
    def is_retry_candidate(self): return self.raw is not None and self.value is None
```

`is_retry_candidate=True` 意味着 JSON 解析 OK 但 Pydantic 校验失败 → **值得重试一次让 LLM 自修**(成功率 70%+)。

### 7.3 `llm/schemas.py` — Pydantic 输出模型

`LLMScoreOutput` 定义评分输出的硬约束:

| 校验 | 规则 |
|---|---|
| 范围 | dimension_scores 每个值 0-100 整数 |
| 键完整 | 只允许 DIMENSION_KEYS 里的键,其他报错 |
| **内部一致** | compliance ≥85 时 weakness_tags 不能含"合规"/"风险",risk_terms 必须空 |

这是抓最严重的幻觉:LLM 给了 95 分合规,但又顺手在 weakTags 写"合规风险"——典型自相矛盾。

### 7.4 `llm/retry.py` — 重试策略

```python
call_with_retry(fn, label, on_retry) → T
   ├─ 重试条件: RateLimitError / APITimeoutError / APIConnectionError / 5xx
   ├─ 不重试: 401 / 400 / context too long(这些重试也不会变好)
   ├─ 退避: 1s → 2s → 4s,带 ±20% jitter
   ├─ Retry-After header: 如果有,优先用 API 给的等待时间
   └─ 最多 3 次
```

**关键决策**:`on_retry` 是个回调,让 `metrics` 模块能在重试时打 `rate_limited=True`。

### 7.5 `llm/metrics.py` — 可观测性

每次 LLM 调用都被 `llm_call_tracker` 上下文管理器包裹:

```python
async with llm_call_tracker(method="finish", scene_id="INS_PERIODIC", model="deepseek-chat") as rec:
    resp = await client.chat.completions.create(...)
    rec.input_tokens = resp.usage.prompt_tokens
    rec.cached_tokens = resp.usage.prompt_cache_hit_tokens   # ← DeepSeek 缓存命中数
    rec.success = True
# 退出时自动:
#   - logger.info("llm_call", extra=rec.as_log_extra())     ← 结构化日志
#   - 累加到进程级 _aggregates 桶                            ← /metrics/llm 暴露
```

进程级聚合可以通过 `GET /metrics/llm` 接口实时查看,详见 [system_overview §9](../system_overview.md)。

## 8. 添加新场景的 5 步法(per-scene builder 时代)

假设要加一个"管理员答疑"场景:

```python
# 1. 在 prompts/admin_qa.py 写 3 个层
class AdminQAPersonaLayer(PromptLayer):
    name = "L1_persona_admin_qa"
    is_dynamic = False
    def render(self, ctx): return "你是后台答疑专家..."

class AdminQAInstructionLayer(PromptLayer):
    name = "L3_instruction_admin_qa"
    is_dynamic = False
    def render(self, ctx): return "## L3 任务\n... + 几个判断示例..."

class AdminQAContextLayer(PromptLayer):
    name = "L2_context_admin_qa"
    is_dynamic = True
    def render(self, ctx): return f"## 问题: {ctx['question']}..."  # 只放真正动态的内容

# 2. (可选)在 boundaries.py 加 AdminQABoundaryLayer + 反例清单
# 3. (可选)在 formats.py 加 AdminQAFormatLayer + 正反示例
# 4. (可选)在 scene_anchor.py 加 AdminQASceneAnchorLayer(如果有 scene-stable 内容)
class AdminQASceneAnchorLayer(PromptLayer):
    is_dynamic = False
    def __init__(self, scene_config, scene_id):
        self.scene_config = scene_config
        self.scene_id = scene_id
        self.name = f"L2anchor_admin_qa__{scene_id}"
    def render(self, ctx): return f"## scene 配置\n{self.scene_config}..."

# 5. 在 prompts/admin_qa.py 写 per-scene builder 工厂 + 缓存
def build_admin_qa_builder(scene_config, scene_id):
    return LayeredPromptBuilder(
        system_layer=AdminQAPersonaLayer(),
        user_layers=[
            AdminQAInstructionLayer(),
            GlobalBoundaryLayer(),                      # 复用
            AdminQABoundaryLayer(),                     # 新加
            AdminQAFormatLayer(),                       # 新加
            AdminQASceneAnchorLayer(scene_config, scene_id),  # 静态,scene-stable
            AdminQAContextLayer(),                       # 动态
        ],
    )

_ADMIN_QA_BUILDER_CACHE: dict[str, LayeredPromptBuilder] = {}
def get_admin_qa_builder(scene_config, scene_id):
    if scene_id not in _ADMIN_QA_BUILDER_CACHE:
        _ADMIN_QA_BUILDER_CACHE[scene_id] = build_admin_qa_builder(scene_config, scene_id)
    return _ADMIN_QA_BUILDER_CACHE[scene_id]

# 在调用方
builder = get_admin_qa_builder(scene_config, scene_id="some_scene")
messages = builder.to_chat_messages({"question": "..."})
```

L1/L3/L4_scene/L5/L2-Anchor/L2 六层职责清晰,L4_global 直接复用,**新场景不需要碰任何现有 prompt**。**每个 scene 各自一个 builder 实例**,SceneAnchor 字节稳定 → cache 命中。

## 9. 调优入口速查

| 想改什么 | 改哪里 |
|---|---|
| 评分专家身份 | `prompts/scorer.py` `ScorerPersonaLayer` |
| 客户角色框架 | `prompts/customer.py` `CustomerPersonaLayer` |
| 评分任务 CoT 步骤 + 示例 | `prompts/scorer.py` `ScorerInstructionLayer` |
| 客户决策树优先级 + 示例 | `prompts/customer.py` `CustomerInstructionLayer` |
| 全局反幻觉规则 + 反例 | `prompts/boundaries.py` `GlobalBoundaryLayer` |
| 评分场景专属硬约束 + 红线词表 | `prompts/boundaries.py` `ScorerBoundaryLayer` |
| 客户场景专属硬约束 + AI 出戏反例 | `prompts/boundaries.py` `CustomerBoundaryLayer` |
| 评分输出 JSON schema + 正反示例 | `prompts/formats.py` `ScorerFormatLayer` |
| 客户输出形态约束 + 好/坏示例 | `prompts/formats.py` `CustomerFormatLayer` |
| **评分场景 rubric 锚定层** | `prompts/scene_anchor.py` `ScorerSceneAnchorLayer` |
| **客户场景画像锚定层** | `prompts/scene_anchor.py` `CustomerSceneAnchorLayer` |
| finish 评分看到的对话格式 | `prompts/scorer.py` `FinishContextLayer.render` |
| reply 评分看到的内容 | `prompts/scorer.py` `ReplyContextLayer.render` |
| 客户模拟看到的上下文 | `prompts/customer.py` `CustomerContextLayer.render` |
| Pydantic 输出模型 | `llm/schemas.py` `LLMScoreOutput` |
| 重试策略 | `llm/retry.py` `_MAX_ATTEMPTS / _BACKOFF_BASE` |
| 解析兜底链 | `llm/parser.py` `parse_json_lenient` |
| AsyncOpenAI 客户端配置 | `llm/client.py` `get_async_client` |

## 10. 已知限制与待办

| 问题 | 现状 | 路径 |
|---|---|---|
| 改 L4 边界没有 CI 验证(可能破坏多个场景) | 已知 | 加 prompt 渲染快照测试 |
| Pydantic schema 与 prompt L5 描述靠人工同步 | 已知 | 用 `model_json_schema()` 自动生成 L5 |
| 静态缓存没 TTL,改完 prompt 需要重启进程 | 已知 | 设计取舍,生产环境本来就重启 |
| 加新场景需要写多个文件 | 已知 | 5 步法已经把成本降到很低 |
| 没有 prompt A/B 测试框架 | 已知 | 后续可基于 builder 实例做 |

## 11. 演示亮点

跑下面的代码,亲眼看到 5 层架构:

```python
from app.core.llm.prompts.scorer import build_finish_scorer_builder

builder = build_finish_scorer_builder()
rendered = builder.build({
    "answer": "...",
    "criterion": {...},
    "coverage": {...},
    "reference_items": [...],
    "dialog_pairs": [...],
})
print("--- SYSTEM (L1) ---")
print(rendered.system)
print("--- USER (L3 → L4×2 → L5 → L2) ---")
print(rendered.user)
print("--- 静态缓存 keys ---")
print(sorted(builder._static_cache.keys()))
# ['L1_persona_scorer', 'L3_instruction_scorer', 'L4_boundary_global',
#  'L4_boundary_scorer', 'L5_format_scorer']
# L2 不在缓存里(它是动态的)
```

可以亲眼看到 5 层结构清晰可读,静态层的 5 个 keys 都被缓存。
