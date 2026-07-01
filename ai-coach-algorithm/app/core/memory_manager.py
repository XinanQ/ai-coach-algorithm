from __future__ import annotations

from typing import Any

from app.core.memory_store import HybridLongTermMemoryStore, HybridShortTermMemoryStore
from app.utils.file_loader import now_iso


class MemoryManager:
    def __init__(
        self,
        short_store: HybridShortTermMemoryStore | None = None,
        long_store: HybridLongTermMemoryStore | None = None,
    ) -> None:
        self.short_store = short_store or HybridShortTermMemoryStore()
        self.long_store = long_store or HybridLongTermMemoryStore()

    def status(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "short_term_memory": self.short_store.state.to_dict(),
            "long_term_memory": self.long_store.state.to_dict(),
            "short_term_target": "Redis session state with JSON hot backup",
            "long_term_target": "PostgreSQL training memory with JSON safety fallback",
        }
        if hasattr(self.long_store, "vector_status"):
            result["vector_memory"] = self.long_store.vector_status()
        return result

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self.short_store.get(session_id)

    def upsert_session(self, session: dict[str, Any]) -> dict[str, Any]:
        session.setdefault("created_at", now_iso())
        return self.short_store.upsert(session)

    def append_message(self, session_id: str, role: str, content: str) -> dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            raise KeyError(f"session not found: {session_id}")
        messages = session.setdefault("messages", [])
        messages.append({"role": role, "content": content, "created_at": now_iso()})
        return self.upsert_session(session)

    def save_longterm(self, record: dict[str, Any]) -> dict[str, Any]:
        return self.long_store.append(record)

    def list_longterm(self, user_id: str | None = None, scenario_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        return self.long_store.list(user_id=user_id, scenario_id=scenario_id, limit=limit)

    def retrieve_history(
        self,
        query: str,
        user_id: str | None = None,
        scenario_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return self.long_store.retrieve(query=query, user_id=user_id, scenario_id=scenario_id, limit=limit)


_MEMORY_MANAGER: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    global _MEMORY_MANAGER
    if _MEMORY_MANAGER is None:
        _MEMORY_MANAGER = MemoryManager()
    return _MEMORY_MANAGER


def reset_memory_manager() -> None:
    global _MEMORY_MANAGER
    _MEMORY_MANAGER = None

