from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.embedding_adapter import EmbeddingAdapter
from app.core.text_cleaner import clean_text
from app.utils.file_loader import now_iso, read_json, resolve_path, write_json


VECTOR_ROOT = Path("data/vector_store")
CHROMA_DIR = VECTOR_ROOT / "chroma"
MANIFEST_PATH = VECTOR_ROOT / "marketing_vector_manifest.json"
JSON_MIRROR_PATH = Path("data/marketing_vector_index.json")


@dataclass(frozen=True)
class VectorBuildResult:
    backend: str
    model: str
    dimensions: int
    tutor_collection: str
    customer_collection: str
    chunk_count: int
    persist_dir: str
    manifest_path: str
    embedding_adapter: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "model": self.model,
            "dimensions": self.dimensions,
            "collections": {
                "tutor": self.tutor_collection,
                "customer": self.customer_collection,
            },
            "chunk_count": self.chunk_count,
            "persist_dir": self.persist_dir,
            "manifest_path": self.manifest_path,
            "embedding_adapter": self.embedding_adapter,
        }


def load_vector_manifest() -> dict[str, Any]:
    return read_json(MANIFEST_PATH, default={}) or {}


def _client():
    import chromadb

    persist_dir = resolve_path(CHROMA_DIR)
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist_dir))


def _collection_name(prefix: str, adapter: EmbeddingAdapter) -> str:
    signature = f"{adapter.info.active_backend}:{adapter.info.active_model}:{adapter.dimensions}"
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _metadata_value(value: Any) -> str | int | float | bool:
    if isinstance(value, (str, int, float, bool)):
        return value
    if value is None:
        return ""
    return json.dumps(value, ensure_ascii=False)


def _chunk_metadata(chunk: dict[str, Any]) -> dict[str, str | int | float | bool]:
    keys = [
        "chunk_id",
        "source_section_id",
        "source_file",
        "business_type",
        "business_name",
        "scene_id",
        "scene_name",
        "knowledge_type",
        "title",
        "review_status",
        "compliance_status",
        "enabled",
        "rag_ready",
    ]
    return {key: _metadata_value(chunk.get(key)) for key in keys}


def _tutor_text(chunk: dict[str, Any]) -> str:
    parts = [
        chunk.get("title", ""),
        chunk.get("scene_name", ""),
        chunk.get("business_name", ""),
        chunk.get("tutor_view_text", ""),
        chunk.get("content", ""),
    ]
    return clean_text("\n".join(str(part) for part in parts if part))


def _customer_text(chunk: dict[str, Any]) -> str:
    queries = chunk.get("customer_queries") or []
    if not isinstance(queries, list):
        queries = [str(queries)]
    parts = [
        chunk.get("customer_query", ""),
        "\n".join(str(query) for query in queries),
        chunk.get("customer_view_text", ""),
        chunk.get("title", ""),
        chunk.get("content", ""),
    ]
    return clean_text("\n".join(str(part) for part in parts if part))


class ChromaMarketingVectorStore:
    def __init__(self) -> None:
        self.client = _client()
        self.persist_dir = str(resolve_path(CHROMA_DIR))

    def build(self, chunks: list[dict[str, Any]], adapter: EmbeddingAdapter, force: bool = False) -> dict[str, Any]:
        tutor_collection_name = _collection_name("marketing_tutor", adapter)
        customer_collection_name = _collection_name("marketing_customer", adapter)
        if force:
            for name in [tutor_collection_name, customer_collection_name]:
                try:
                    self.client.delete_collection(name=name)
                except Exception:
                    pass

        tutor_collection = self.client.get_or_create_collection(name=tutor_collection_name, metadata={"hnsw:space": "cosine"})
        customer_collection = self.client.get_or_create_collection(name=customer_collection_name, metadata={"hnsw:space": "cosine"})

        ready_chunks = [
            chunk
            for chunk in chunks
            if chunk.get("enabled", True) is not False and clean_text(chunk.get("content", ""))
        ]
        self._upsert_collection(tutor_collection, ready_chunks, adapter, route="tutor")
        self._upsert_collection(customer_collection, ready_chunks, adapter, route="customer")

        manifest = {
            "version": "marketing_chroma_v4_real_embedding_memory_upgrade",
            "built_at": now_iso(),
            "vector_backend": "chroma",
            "embedding_backend": adapter.info.active_backend,
            "embedding_model": adapter.info.active_model,
            "dimensions": adapter.dimensions,
            "chunk_count": len(ready_chunks),
            "persist_dir": self.persist_dir,
            "collections": {
                "tutor": {"name": tutor_collection_name, "count": tutor_collection.count()},
                "customer": {"name": customer_collection_name, "count": customer_collection.count()},
            },
            "embedding_adapter": adapter.describe(),
        }
        write_json(MANIFEST_PATH, manifest)
        write_json(JSON_MIRROR_PATH, manifest)
        return manifest

    @staticmethod
    def _upsert_collection(collection: Any, chunks: list[dict[str, Any]], adapter: EmbeddingAdapter, route: str) -> None:
        batch_size = 64
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            ids = [f"{route}:{chunk.get('chunk_id', start + idx)}" for idx, chunk in enumerate(batch)]
            documents = [_tutor_text(chunk) if route == "tutor" else _customer_text(chunk) for chunk in batch]
            embeddings = adapter.embed_texts(documents)
            metadatas = [_chunk_metadata(chunk) for chunk in batch]
            collection.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def status(self) -> dict[str, Any]:
        manifest = load_vector_manifest()
        if not manifest:
            return {
                "vector_backend": "chroma",
                "status": "not_built",
                "persist_dir": self.persist_dir,
            }
        collections: dict[str, Any] = {}
        for route, info in (manifest.get("collections") or {}).items():
            name = info.get("name") if isinstance(info, dict) else None
            if not name:
                collections[route] = {"name": "", "count": 0, "available": False}
                continue
            try:
                collection = self.client.get_collection(name=name)
                collections[route] = {"name": name, "count": collection.count(), "available": True}
            except Exception as exc:
                collections[route] = {"name": name, "count": 0, "available": False, "error": str(exc)[:300]}
        return {**manifest, "collections": collections, "status": "ready"}

    def query(
        self,
        collection_name: str,
        query_text: str,
        adapter: EmbeddingAdapter,
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        collection = self.client.get_collection(name=collection_name)
        kwargs: dict[str, Any] = {
            "query_embeddings": [adapter.embed_query(query_text)],
            "n_results": max(1, min(top_k, 20)),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        result = collection.query(**kwargs)
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        items: list[dict[str, Any]] = []
        for idx, item_id in enumerate(ids):
            distance = float(distances[idx]) if idx < len(distances) else 1.0
            items.append(
                {
                    "id": item_id,
                    "score": round(1.0 / (1.0 + max(distance, 0.0)), 4),
                    "distance": round(distance, 6),
                    "content": documents[idx] if idx < len(documents) else "",
                    "metadata": metadatas[idx] if idx < len(metadatas) else {},
                    "retrieval_source": "chroma",
                }
            )
        return items
