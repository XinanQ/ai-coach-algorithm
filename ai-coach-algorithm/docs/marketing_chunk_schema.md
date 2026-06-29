# Marketing Chunk Schema

`data/marketing_chunks.json` 是当前营销话术 RAG 的本地知识库主体。它由 `data/marketing_sections.json` 生成。

现在每个 chunk 同时支持两种检索视图：

```text
tutor_view_text
= AI 导师侧检索视图，主要是员工/经理回答话术，用于评分参考、标准表达和合规反馈。

customer_view_text
= AI 客户侧检索视图，主要是客户提问、客户异议或可作为客户追问的标题 fallback。
```

这样做是为了避免把 `title` 永远当作客户提问。`title` 仍然保留为 metadata，但 AI 客户侧会优先使用从正文中抽取的客户句子。

## 生成接口

```text
POST /knowledge/marketing-docs/build-chunks
```

## 核心字段

```json
{
  "chunk_id": "MCH_000001",
  "business_type": "INS",
  "scene_id": "INS_INVITE",
  "knowledge_type": "phone_invitation",
  "title": "到期类客户(以定期为例)",
  "title_type": "section_heading",
  "content": "经理:您好... 客户:好的...",

  "customer_query": "具体什么?",
  "customer_queries": ["是什么?", "具体什么?"],
  "customer_view_text": "是什么?\n具体什么?",
  "customer_view_source": "dialogue_customer_lines",
  "customer_search_text": "是什么?\n具体什么?",

  "tutor_view_text": "您好，请问是XX吗?...",
  "tutor_view_source": "dialogue_employee_lines",
  "tutor_search_text": "您好，请问是XX吗?...",

  "compliance_status": "pass",
  "risk_terms": [],
  "review_status": "pending",
  "rag_ready": false
}
```

## 字段说明

- `title`: 来源 section 标题，不保证一定是客户提问。
- `title_type`: 标题类型，目前包括 `section_heading`、`section_heading_with_customer_dialogue`、`customer_question`。
- `content`: 原始 chunk 正文，保留完整上下文。
- `customer_query`: 从客户话语中抽取出的第一条代表性问题；没有则为空。
- `customer_queries`: 从正文客户角色中抽取出的客户问题/异议列表。
- `customer_view_text`: AI 客户侧检索文本，优先来自客户角色话语；没有客户话语时使用标题 fallback。
- `customer_view_source`: `customer_view_text` 的来源，例如 `dialogue_customer_lines`、`speaker_title`、`question_like_title`、`section_title_fallback`。
- `tutor_view_text`: AI 导师侧检索文本，优先来自员工/经理话术；没有角色话术时使用完整 content。
- `tutor_view_source`: `tutor_view_text` 的来源，例如 `dialogue_employee_lines`、`content_fallback`。
- `tutor_search_text`: 导师侧 RAG 使用的主检索字段。
- `customer_search_text`: 客户侧 RAG 使用的主检索字段。
- `search_text`: 兼容旧逻辑的 `title + content` 字段，后续不作为两条 RAG 的主字段。

## 使用边界

```text
AI 导师 RAG
-> 主要检索 tutor_search_text / tutor_view_text

AI 客户 RAG
-> 主要检索 customer_search_text / customer_view_text / customer_query
```
