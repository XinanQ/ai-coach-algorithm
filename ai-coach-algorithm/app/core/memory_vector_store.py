"""长期记忆的向量化存储与语义检索。

复用项目已有的 ChromaDB + EmbeddingAdapter 基础设施，为 longterm_memory
新建一个独立 collection（memory_longterm_<hash>），在每次 save_longterm 时
同步写入 embedding，在 retrieve_history 时用语义检索替代 lexical_similarity。

设计要点：
  - collection 按 embedding 模型签名命名（换模型自动新建，不会污染旧索引）
  - 写入失败静默降级（不影响 JSON/PG 主存储）
  - 检索失败自动 fallback 到 lexical_similarity
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.core.embedding_adapter import EmbeddingAdapter, get_embedding_adapter
from app.core.text_cleaner import clean_text

logger = logging.getLogger(__name__)

MEMORY_COLLECTION_PREFIX = "memory_longterm"


def _collection_name(adapter: EmbeddingAdapter) -> str:
    sig = f"{adapter.info.active_backend}:{adapter.info.active_model}:{adapter.dimensions}"
    digest = hashlib.sha1(sig.encode("utf-8")).hexdigest()[:12]
    return f"{MEMORY_COLLECTION_PREFIX}_{digest}"


def _memory_text(record: dict[str, Any]) -> str:
    """把一条 longterm_memory 记录拼成可 embedding 的文本。"""
    parts = [
        record.get("summary", ""),
        record.get("feedback", ""),
    ]
    tags = record.get("weakness_tags") or []
    if isinstance(tags, list):
        parts.append(" ".join(str(t) for t in tags))
    score_result = record.get("score_result") or {}
    suggestion = score_result.get("suggestion", "")
    if suggestion:
        parts.append(suggestion)
    return clean_text(" ".join(str(p) for p in parts if p))


def _record_metadata(record: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """提取可存入 ChromaDB metadata 的字段（只支持简单类型）。"""
    meta: dict[str, str | int | float | bool] = {}
    for key in ("memory_id", "user_id", "scenario_id", "customer_id", "customer_type"):
        val = record.get(key)
        if val is not None:
            meta[key] = str(val)
    score = record.get("score")
    if score is not None:
        try:
            meta["score"] = float(score)
        except (TypeError, ValueError):
            pass
    tags = record.get("weakness_tags") or []
    if isinstance(tags, list):
        meta["weakness_tags_str"] = ",".join(str(t) for t in tags)
    return meta


class MemoryVectorStore:
    """长期记忆的 ChromaDB 向量索引。"""

    def __init__(self, adapter: EmbeddingAdapter | None = None) -> None:
        self._adapter = adapter or get_embedding_adapter()
        self._collection_name = _collection_name(self._adapter)
        self._collection: Any = None
        self._available = False
        try:
            import chromadb
            from app.core.chroma_vector_store import CHROMA_DIR
            from app.utils.file_loader import resolve_path

            persist_dir = resolve_path(CHROMA_DIR)
            persist_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(persist_dir))
            self._collection = client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
        except Exception as exc:
            logger.warning("MemoryVectorStore init failed (will use lexical fallback): %s", exc)

    @property
    def available(self) -> bool:
        return self._available

    def upsert(self, record: dict[str, Any]) -> bool:
        """写入/更新一条记忆的 embedding。成功返回 True，失败静默返回 False。"""
        if not self._available:
            return False
        memory_id = record.get("memory_id")
        if not memory_id:
            return False
        text = _memory_text(record)
        if not text.strip():
            return False
        try:
            embedding = self._adapter.embed_query(text)
            self._collection.upsert(
                ids=[str(memory_id)],
                documents=[text],
                embeddings=[embedding],
                metadatas=[_record_metadata(record)],
            )
            return True
        except Exception as exc:
            logger.warning("MemoryVectorStore upsert failed for %s: %s", memory_id, exc)
            return False

    def query(
        self,
        query_text: str,
        user_id: str | None = None,
        scenario_id: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """语义检索历史训练记录。返回 [{memory_id, score, text, metadata}, ...]。"""
        if not self._available or not query_text.strip():
            return []
        try:
            embedding = self._adapter.embed_query(query_text)
            where_clauses: list[dict[str, Any]] = []
            if user_id:
                where_clauses.append({"user_id": {"$eq": str(user_id)}})
            if scenario_id:
                where_clauses.append({"scenario_id": {"$eq": str(scenario_id)}})

            kwargs: dict[str, Any] = {
                "query_embeddings": [embedding],
                "n_results": max(1, min(limit, 50)),
                "include": ["documents", "metadatas", "distances"],
            }
            if len(where_clauses) == 1:
                kwargs["where"] = where_clauses[0]
            elif len(where_clauses) > 1:
                kwargs["where"] = {"$and": where_clauses}

            result = self._collection.query(**kwargs)

            ids = result.get("ids", [[]])[0]
            documents = result.get("documents", [[]])[0]
            metadatas = result.get("metadatas", [[]])[0]
            distances = result.get("distances", [[]])[0]

            items: list[dict[str, Any]] = []
            for idx, item_id in enumerate(ids):
                dist = float(distances[idx]) if idx < len(distances) else 1.0
                items.append({
                    "memory_id": item_id,
                    "retrieval_score": round(1.0 / (1.0 + max(dist, 0.0)), 4),
                    "distance": round(dist, 6),
                    "text": documents[idx] if idx < len(documents) else "",
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    "retrieval_source": "chroma_memory",
                })
            return items
        except Exception as exc:
            logger.warning("MemoryVectorStore query failed: %s", exc)
            return []

    def count(self) -> int:
        if not self._available:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    def status(self) -> dict[str, Any]:
        return {
            "available": self._available,
            "collection_name": self._collection_name,
            "count": self.count(),
            "embedding_backend": self._adapter.info.active_backend,
            "embedding_model": self._adapter.info.active_model,
            "dimensions": self._adapter.dimensions,
        }


_STORE_CACHE: MemoryVectorStore | None = None


def get_memory_vector_store() -> MemoryVectorStore:
    global _STORE_CACHE
    if _STORE_CACHE is None:
        _STORE_CACHE = MemoryVectorStore()
    return _STORE_CACHE


def reset_memory_vector_store() -> None:
    global _STORE_CACHE
    _STORE_CACHE = None
