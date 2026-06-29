# 文档索引

按读者目的快速定位。

## 我是新接手的算法同事 / 想全面了解系统

→ 先读 **[system_overview.md](system_overview.md)** —— 14 章覆盖架构 / 数据流 / 模块组织 / 3 层记忆 / 自适应难度 / 失败回退 / 配置 / 可观测性

→ 再按需读各算法子模块文档(见下)

## 我是 Java 后端 / 要对接小程序

→ 读 **[backend_integration_guide.md](backend_integration_guide.md)** —— 字段映射 / camelCase 适配 / 业务字段 mock 说明

## 我要修改某一块算法

每个算法模块都有独立技术文档,包含数据流、参数、调优入口:

| 文档 | 涉及代码 | 改这里看这本 |
|---|---|---|
| **[algorithms/01_dual_rag.md](algorithms/01_dual_rag.md)** | `marketing_rag.py` + `coverage.py` | 改 HyDE 检索 / gap 检测 / 覆盖率算法 |
| **[algorithms/02_scoring.md](algorithms/02_scoring.md)** | `rule_scorer.py` + `llm_scorer.py` | 改评分维度 / 权重 / Pydantic 校验 |
| **[algorithms/03_customer_simulation.md](algorithms/03_customer_simulation.md)** | `llm_customer.py` | 改 LLM 客户模拟 / 模板兜底 |
| **[algorithms/04_intent_understanding.md](algorithms/04_intent_understanding.md)** | `customer_answer_understanding.py` + `intent_*` | 改意图标签 / 关键词 / 阈值 / BERT 训练 |
| **[algorithms/05_prompt_architecture.md](algorithms/05_prompt_architecture.md)** | `llm/prompts/*` | 改 5 层 prompt 任一层 / 加新场景 builder |
| **[algorithms/06_memory_and_adaptive.md](algorithms/06_memory_and_adaptive.md)** | `weakness_profile.py` + `memory_vector_store.py` + `adaptive_difficulty.py` | 改弱点画像 / 向量记忆检索 / 自适应难度 |

## 我要标注数据 / 改数据规范

| 文档 | 内容 |
|---|---|
| **[intent_annotation_schema.md](intent_annotation_schema.md)** | 6 个意图标签的定义、标注原则、字段格式 |
| **[data_dictionary.md](data_dictionary.md)** | 原始话术资料的字段说明(`standard_scripts.csv` 等) |
| **[marketing_chunk_schema.md](marketing_chunk_schema.md)** | `marketing_chunks.json` 的 chunk 结构 |
| **[marketing_business_config.md](marketing_business_config.md)** | 业务线配置文件(`configs/marketing_business_config.json`)说明 |

## 我要演示系统 / 试用

→ 仓库根目录 **[../README.md](../README.md)** 的"试用流程"章节
