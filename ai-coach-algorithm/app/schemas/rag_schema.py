from __future__ import annotations

from pydantic import BaseModel, Field


class VectorIndexBuildRequest(BaseModel):
    force: bool = False
    embedding_backend: str | None = Field(default=None, examples=["sentence_transformers"])
    embedding_model: str | None = Field(default=None, examples=["BAAI/bge-small-zh-v1.5"])
    dimensions: int | None = None
    local_files_only: bool | None = None


class VectorRetrieveRequest(BaseModel):
    query: str
    route: str = "tutor"
    top_k: int = 5
    scene_id: str | None = None


class CustomerAnswerUnderstandingRequest(BaseModel):
    text: str

