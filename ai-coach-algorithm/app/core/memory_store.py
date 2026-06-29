from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.text_cleaner import lexical_similarity
from app.utils.file_loader import now_iso, read_json, resolve_path, write_json


SHORT_MEMORY_JSON = "mock_db/mock_dialog_sessions.json"
LONG_MEMORY_JSON = "mock_db/longterm_memory.json"


@dataclass
class BackendState:
    requested_backend: str
    active_backend: str
    available: bool
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_backend": self.requested_backend,
            "active_backend": self.active_backend,
            "available": self.available,
            "fallback_reason": self.fallback_reason,
        }


class JsonShortTermMemoryStore:
    def __init__(self, path: str = SHORT_MEMORY_JSON) -> None:
        self.path = path

    def get(self, session_id: str) -> dict[str, Any] | None:
        data = read_json(self.path, default={}) or {}
        item = data.get(session_id)
        return item if isinstance(item, dict) else None

    def upsert(self, session: dict[str, Any]) -> dict[str, Any]:
        session_id = session.get("session_id") or f"S_{uuid.uuid4().hex[:12]}"
        session["session_id"] = session_id
        session["updated_at"] = now_iso()
        data = read_json(self.path, default={}) or {}
        data[session_id] = session
        write_json(self.path, data)
        return session

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        data = read_json(self.path, default={}) or {}
        items = [item for item in data.values() if isinstance(item, dict)]
        return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)[:limit]


class RedisShortTermMemoryStore:
    def __init__(self, url: str, ttl_seconds: int = 86400, key_prefix: str = "ai_coach:session") -> None:
        import redis

        self.redis = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.5, socket_timeout=1.0)
        self.redis.ping()
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

    def _key(self, session_id: str) -> str:
        return f"{self.key_prefix}:{session_id}"

    def get(self, session_id: str) -> dict[str, Any] | None:
        import json

        raw = self.redis.get(self._key(session_id))
        return json.loads(raw) if raw else None

    def upsert(self, session: dict[str, Any]) -> dict[str, Any]:
        import json

        session_id = session.get("session_id") or f"S_{uuid.uuid4().hex[:12]}"
        session["session_id"] = session_id
        session["updated_at"] = now_iso()
        self.redis.setex(self._key(session_id), self.ttl_seconds, json.dumps(session, ensure_ascii=False))
        return session

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        import json

        items: list[dict[str, Any]] = []
        for key in self.redis.scan_iter(f"{self.key_prefix}:*", count=limit):
            raw = self.redis.get(key)
            if raw:
                items.append(json.loads(raw))
            if len(items) >= limit:
                break
        return sorted(items, key=lambda item: item.get("updated_at", ""), reverse=True)[:limit]


class HybridShortTermMemoryStore:
    def __init__(self, json_path: str = SHORT_MEMORY_JSON) -> None:
        requested = os.getenv("AI_COACH_SHORT_MEMORY_BACKEND", "auto").lower()
        self.json_store = JsonShortTermMemoryStore(json_path)
        self.primary: JsonShortTermMemoryStore | RedisShortTermMemoryStore = self.json_store
        self.state = BackendState(requested_backend=requested, active_backend="json", available=True)
        if requested in {"auto", "redis"}:
            redis_url = os.getenv("AI_COACH_REDIS_URL")
            if redis_url:
                try:
                    self.primary = RedisShortTermMemoryStore(
                        redis_url,
                        ttl_seconds=int(os.getenv("AI_COACH_SESSION_TTL_SECONDS", "86400")),
                    )
                    self.state = BackendState(requested_backend=requested, active_backend="redis", available=True)
                except Exception as exc:
                    self.state = BackendState(
                        requested_backend=requested,
                        active_backend="json",
                        available=True,
                        fallback_reason=f"redis unavailable: {type(exc).__name__}: {exc}"[:500],
                    )

    def get(self, session_id: str) -> dict[str, Any] | None:
        item = self.primary.get(session_id)
        if item is None and self.primary is not self.json_store:
            return self.json_store.get(session_id)
        return item

    def upsert(self, session: dict[str, Any]) -> dict[str, Any]:
        saved = self.primary.upsert(session)
        if self.primary is not self.json_store:
            self.json_store.upsert(saved)
        return saved

    def list_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.primary.list_recent(limit=limit)


class JsonLongTermMemoryStore:
    def __init__(self, path: str = LONG_MEMORY_JSON) -> None:
        self.path = path

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        data = read_json(self.path, default=[]) or []
        memory_id = record.get("memory_id") or f"MEM_{uuid.uuid4().hex[:12]}"
        record = {**record, "memory_id": memory_id, "updated_at": now_iso(), "saved_at": now_iso()}
        data = [item for item in data if item.get("memory_id") != memory_id]
        data.append(record)
        write_json(self.path, data)
        return record

    def list(self, user_id: str | None = None, scenario_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        data = read_json(self.path, default=[]) or []
        items = [item for item in data if isinstance(item, dict)]
        if user_id:
            items = [item for item in items if item.get("user_id") == user_id]
        if scenario_id:
            items = [item for item in items if item.get("scenario_id") == scenario_id or item.get("scene_id") == scenario_id]
        return sorted(items, key=lambda item: item.get("saved_at") or item.get("updated_at") or "", reverse=True)[:limit]

    def retrieve(self, query: str, user_id: str | None = None, scenario_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        candidates = self.list(user_id=user_id, scenario_id=scenario_id, limit=200)
        ranked = []
        for item in candidates:
            text = " ".join(
                str(part)
                for part in [item.get("summary", ""), item.get("feedback", ""), item.get("weakness_tags", "")]
            )
            ranked.append({**item, "retrieval_score": lexical_similarity(query, text)})
        return sorted(ranked, key=lambda item: item.get("retrieval_score", 0), reverse=True)[:limit]


class PostgresLongTermMemoryStore:
    def __init__(self, dsn: str) -> None:
        import psycopg

        self.psycopg = psycopg
        self.dsn = dsn
        self._ensure_schema()

    def _connect(self):
        return self.psycopg.connect(self.dsn, autocommit=True)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists ai_coach_longterm_memory (
                    memory_id text primary key,
                    session_id text,
                    user_id text,
                    scenario_id text,
                    customer_id text,
                    customer_type text,
                    score double precision,
                    weakness_tags jsonb not null default '[]'::jsonb,
                    summary text,
                    feedback text,
                    messages jsonb not null default '[]'::jsonb,
                    score_result jsonb not null default '{}'::jsonb,
                    raw_record jsonb not null default '{}'::jsonb,
                    created_at timestamptz not null default now(),
                    updated_at timestamptz not null default now()
                )
                """
            )
            conn.execute("create index if not exists idx_ai_coach_memory_user on ai_coach_longterm_memory(user_id)")
            conn.execute("create index if not exists idx_ai_coach_memory_scenario on ai_coach_longterm_memory(scenario_id)")

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        from psycopg.types.json import Json

        memory_id = record.get("memory_id") or f"MEM_{uuid.uuid4().hex[:12]}"
        score_result = record.get("score_result") or {}
        score = record.get("score") or score_result.get("total_score")
        record = {**record, "memory_id": memory_id, "updated_at": now_iso(), "saved_at": now_iso()}
        with self._connect() as conn:
            conn.execute(
                """
                insert into ai_coach_longterm_memory (
                    memory_id, session_id, user_id, scenario_id, customer_id, customer_type,
                    score, weakness_tags, summary, feedback, messages, score_result, raw_record, updated_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                on conflict (memory_id) do update set
                    session_id = excluded.session_id,
                    user_id = excluded.user_id,
                    scenario_id = excluded.scenario_id,
                    customer_id = excluded.customer_id,
                    customer_type = excluded.customer_type,
                    score = excluded.score,
                    weakness_tags = excluded.weakness_tags,
                    summary = excluded.summary,
                    feedback = excluded.feedback,
                    messages = excluded.messages,
                    score_result = excluded.score_result,
                    raw_record = excluded.raw_record,
                    updated_at = now()
                """,
                (
                    memory_id,
                    record.get("session_id"),
                    record.get("user_id"),
                    record.get("scenario_id") or record.get("scene_id"),
                    record.get("customer_id"),
                    record.get("customer_type"),
                    score,
                    Json(record.get("weakness_tags") or []),
                    record.get("summary"),
                    record.get("feedback"),
                    Json(record.get("messages") or record.get("dialogue_messages") or []),
                    Json(score_result),
                    Json(record),
                ),
            )
        return record

    def list(self, user_id: str | None = None, scenario_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        clauses = []
        params: list[Any] = []
        if user_id:
            clauses.append("user_id = %s")
            params.append(user_id)
        if scenario_id:
            clauses.append("scenario_id = %s")
            params.append(scenario_id)
        where = "where " + " and ".join(clauses) if clauses else ""
        params.append(limit)
        sql = f"select raw_record from ai_coach_longterm_memory {where} order by updated_at desc limit %s"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row[0]) for row in rows]

    def retrieve(self, query: str, user_id: str | None = None, scenario_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        candidates = self.list(user_id=user_id, scenario_id=scenario_id, limit=200)
        ranked = []
        for item in candidates:
            text = " ".join(str(part) for part in [item.get("summary", ""), item.get("feedback", ""), item.get("weakness_tags", "")])
            ranked.append({**item, "retrieval_score": lexical_similarity(query, text)})
        return sorted(ranked, key=lambda item: item.get("retrieval_score", 0), reverse=True)[:limit]


class HybridLongTermMemoryStore:
    def __init__(self, json_path: str = LONG_MEMORY_JSON) -> None:
        requested = os.getenv("AI_COACH_LONG_MEMORY_BACKEND", "auto").lower()
        self.json_store = JsonLongTermMemoryStore(json_path)
        self.primary: JsonLongTermMemoryStore | PostgresLongTermMemoryStore = self.json_store
        self.state = BackendState(requested_backend=requested, active_backend="json", available=True)
        if requested in {"auto", "postgres", "postgresql"}:
            dsn = os.getenv("AI_COACH_POSTGRES_DSN")
            if dsn:
                try:
                    self.primary = PostgresLongTermMemoryStore(dsn)
                    self.state = BackendState(requested_backend=requested, active_backend="postgresql", available=True)
                except Exception as exc:
                    self.state = BackendState(
                        requested_backend=requested,
                        active_backend="json",
                        available=True,
                        fallback_reason=f"postgres unavailable: {type(exc).__name__}: {exc}"[:500],
                    )

        self._vector_store: Any = None
        try:
            from app.core.memory_vector_store import get_memory_vector_store
            self._vector_store = get_memory_vector_store()
        except Exception:
            pass

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        saved = self.primary.append(record)
        if self.primary is not self.json_store:
            self.json_store.append(saved)
        if self._vector_store is not None:
            self._vector_store.upsert(saved)
        return saved

    def list(self, user_id: str | None = None, scenario_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        return self.primary.list(user_id=user_id, scenario_id=scenario_id, limit=limit)

    def retrieve(self, query: str, user_id: str | None = None, scenario_id: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        if self._vector_store is not None and self._vector_store.available:
            vector_hits = self._vector_store.query(
                query_text=query, user_id=user_id, scenario_id=scenario_id, limit=limit,
            )
            if vector_hits:
                hit_ids = {h["memory_id"] for h in vector_hits}
                score_map = {h["memory_id"]: h["retrieval_score"] for h in vector_hits}
                all_records = self.primary.list(user_id=user_id, scenario_id=scenario_id, limit=200)
                record_map = {r.get("memory_id"): r for r in all_records if r.get("memory_id")}
                results = []
                for mid in hit_ids:
                    rec = record_map.get(mid)
                    if rec:
                        results.append({**rec, "retrieval_score": score_map[mid], "retrieval_source": "vector"})
                return sorted(results, key=lambda x: x.get("retrieval_score", 0), reverse=True)[:limit]
        return self.primary.retrieve(query=query, user_id=user_id, scenario_id=scenario_id, limit=limit)

    def vector_status(self) -> dict[str, Any]:
        if self._vector_store is None:
            return {"available": False, "reason": "vector store not initialized"}
        return self._vector_store.status()

