from __future__ import annotations

from fastapi import FastAPI

from app.api.dialog_api import router as dialog_router
from app.api.memory_api import router as memory_router
from app.api.metrics_api import router as metrics_router
from app.api.practice_api import router as practice_router
from app.api.rag_api import router as rag_router
from app.api.tutor_api import router as tutor_router
from app.core.embedding_adapter import DEFAULT_REAL_BACKEND, DEFAULT_REAL_MODEL
from app.core.embedding_builder import get_marketing_vector_index_status
from app.core.memory_manager import get_memory_manager


app = FastAPI(
    title="Financial AI Coach Algorithm",
    version="4.0.0",
    description="金融绩效驱动 AI 陪练：中文 embedding + Chroma RAG + Redis/PostgreSQL memory adapters.",
)

app.include_router(rag_router)
app.include_router(practice_router)
app.include_router(dialog_router)
app.include_router(memory_router)
app.include_router(tutor_router)
app.include_router(metrics_router)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "embedding_default": {"backend": DEFAULT_REAL_BACKEND, "model": DEFAULT_REAL_MODEL},
        "vector_store": get_marketing_vector_index_status(),
        "memory": get_memory_manager().status(),
    }

