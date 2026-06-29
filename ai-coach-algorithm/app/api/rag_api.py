from __future__ import annotations

from fastapi import APIRouter

from app.core.customer_answer_understanding import analyze_customer_answer
from app.core.embedding_builder import build_marketing_vector_index, get_marketing_vector_index_status
from app.core.marketing_rag import retrieve_marketing_knowledge
from app.schemas.rag_schema import CustomerAnswerUnderstandingRequest, VectorIndexBuildRequest, VectorRetrieveRequest


router = APIRouter(prefix="/rag/marketing", tags=["marketing-rag"])


@router.post("/vector-index/build")
def build_vector_index(request: VectorIndexBuildRequest) -> dict[str, object]:
    return build_marketing_vector_index(
        force=request.force,
        embedding_backend=request.embedding_backend,
        embedding_model=request.embedding_model,
        dimensions=request.dimensions,
        local_files_only=request.local_files_only,
    )


@router.get("/vector-index/status")
def vector_index_status() -> dict[str, object]:
    return get_marketing_vector_index_status()


@router.post("/vector-retrieve")
def vector_retrieve(request: VectorRetrieveRequest) -> dict[str, object]:
    return retrieve_marketing_knowledge(
        query=request.query,
        route=request.route,
        top_k=request.top_k,
        scene_id=request.scene_id,
    )


@router.post("/customer-answer-understanding")
def customer_answer_understanding(request: CustomerAnswerUnderstandingRequest) -> dict[str, object]:
    return analyze_customer_answer(request.text)

