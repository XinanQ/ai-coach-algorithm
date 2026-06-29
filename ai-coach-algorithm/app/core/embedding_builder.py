from __future__ import annotations

from typing import Any

from app.core.chroma_vector_store import ChromaMarketingVectorStore, load_vector_manifest
from app.core.embedding_adapter import DEFAULT_REAL_BACKEND, DEFAULT_REAL_MODEL, get_embedding_adapter
from app.utils.file_loader import read_json


def load_marketing_chunks() -> list[dict[str, Any]]:
    data = read_json("data/marketing_chunks.json", default={}) or {}
    chunks = data.get("chunks", [])
    return chunks if isinstance(chunks, list) else []


def build_marketing_vector_index(
    force: bool = False,
    embedding_backend: str | None = None,
    embedding_model: str | None = None,
    dimensions: int | None = None,
    local_files_only: bool | None = None,
) -> dict[str, Any]:
    adapter = get_embedding_adapter(
        backend=embedding_backend or DEFAULT_REAL_BACKEND,
        model_name=embedding_model or DEFAULT_REAL_MODEL,
        dimensions=dimensions,
        allow_fallback=True,
        local_files_only=local_files_only,
    )
    store = ChromaMarketingVectorStore()
    return store.build(load_marketing_chunks(), adapter=adapter, force=force)


def get_marketing_vector_index_status() -> dict[str, Any]:
    try:
        return ChromaMarketingVectorStore().status()
    except Exception as exc:
        manifest = load_vector_manifest()
        return {
            "status": "error",
            "error": str(exc)[:500],
            "manifest": manifest,
        }

