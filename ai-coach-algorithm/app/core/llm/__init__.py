"""LLM subsystem.

Organized so each concern lives in one file:

  client.py   — sync + async OpenAI-compatible client factories (DeepSeek)
  schemas.py  — Pydantic output models with internal consistency validation
  parser.py   — 3-tier parsing: json.loads → json-repair → Pydantic, with
                a one-shot retry hook for the LLM to self-correct

llm_scorer / llm_customer continue to live at app/core/ and consume these.
"""
