from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SessionUpsertRequest(BaseModel):
    session: dict[str, Any]


class HistoryRetrieveRequest(BaseModel):
    query: str
    user_id: str | None = None
    scenario_id: str | None = None
    limit: int = 5

