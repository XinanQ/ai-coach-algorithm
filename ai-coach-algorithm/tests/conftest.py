"""Test-suite hermeticity: never let unit tests call the paid LLM API.

app/__init__.py auto-loads .env (so local runs and eval pick up
DEEPSEEK_API_KEY without manual exports). Without this fixture that same
mechanism would make unit tests hit DeepSeek whenever a developer's .env has
a key — slow, token-billed, and nondeterministic (the finish `source`
assertion flips to LLM_BASED). Tests must exercise the rule/template paths;
LLM behavior is covered by the eval suites, not pytest.

The preferences are read into module constants at import time, so patching
the environment here would be too late — patch the constants directly.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def hermetic_llm(monkeypatch):
    import app.core.dialog_manager as dialog_manager
    import app.core.llm_customer as llm_customer

    monkeypatch.setattr(dialog_manager, "_SCORER_PREFERENCE", "rule")
    monkeypatch.setattr(dialog_manager, "_CUSTOMER_LLM_PREFERENCE", "template")
    monkeypatch.setattr(llm_customer, "_PREFIX_WARMUP_ENABLED", False)
