from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass
from typing import Iterable

from app.core.text_cleaner import clean_text


DEFAULT_REAL_BACKEND = "sentence_transformers"
DEFAULT_REAL_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_HASH_MODEL = "local_hash_embedding_v1"
DEFAULT_HASH_DIMENSIONS = 384


@dataclass(frozen=True)
class EmbeddingRuntimeInfo:
    requested_backend: str
    requested_model: str
    active_backend: str
    active_model: str
    dimensions: int
    is_fallback: bool = False
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "requested_backend": self.requested_backend,
            "requested_model": self.requested_model,
            "active_backend": self.active_backend,
            "active_model": self.active_model,
            "dimensions": self.dimensions,
            "is_fallback": self.is_fallback,
            "fallback_reason": self.fallback_reason,
        }


class HashEmbeddingModel:
    def __init__(self, dimensions: int = DEFAULT_HASH_DIMENSIONS) -> None:
        self.dimensions = dimensions

    def encode(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        value = clean_text(text)
        vector = [0.0] * self.dimensions
        tokens = self._tokens(value)
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(item * item for item in vector))
        if norm <= 0:
            return vector
        return [round(item / norm, 8) for item in vector]

    @staticmethod
    def _tokens(text: str) -> list[str]:
        chars = [ch for ch in text if not ch.isspace()]
        tokens = chars[:]
        tokens.extend("".join(chars[i : i + 2]) for i in range(max(0, len(chars) - 1)))
        tokens.extend("".join(chars[i : i + 3]) for i in range(max(0, len(chars) - 2)))
        return tokens


class EmbeddingAdapter:
    """Chinese embedding adapter with a deterministic local fallback.

    Default route is a small Chinese sentence-transformers model. The hash model
    stays as a test/dev fallback so the API remains usable on machines without
    model weights, network access, or enough local inference resources.
    """

    def __init__(
        self,
        backend: str | None = None,
        model_name: str | None = None,
        dimensions: int | None = None,
        allow_fallback: bool = True,
        local_files_only: bool | None = None,
    ) -> None:
        requested_backend = (backend or os.getenv("AI_COACH_EMBEDDING_BACKEND") or DEFAULT_REAL_BACKEND).strip()
        requested_model = (
            model_name
            or os.getenv("AI_COACH_EMBEDDING_MODEL")
            or (DEFAULT_HASH_MODEL if requested_backend in {"hash", "local_hash"} else DEFAULT_REAL_MODEL)
        ).strip()
        self.requested_backend = requested_backend
        self.requested_model = requested_model
        self._model: object
        self._is_sentence_transformer = False

        if requested_backend in {"hash", "local_hash"}:
            dim = dimensions or int(os.getenv("AI_COACH_HASH_EMBEDDING_DIM", str(DEFAULT_HASH_DIMENSIONS)))
            self._model = HashEmbeddingModel(dim)
            self.info = EmbeddingRuntimeInfo(
                requested_backend=requested_backend,
                requested_model=requested_model,
                active_backend="local_hash",
                active_model=DEFAULT_HASH_MODEL,
                dimensions=dim,
            )
            return

        if requested_backend != "sentence_transformers":
            if not allow_fallback:
                raise ValueError(f"Unsupported embedding backend: {requested_backend}")
            self._use_hash_fallback(dimensions, f"unsupported backend: {requested_backend}")
            return

        try:
            from sentence_transformers import SentenceTransformer

            if local_files_only is None:
                local_files_only = os.getenv("AI_COACH_MODEL_LOCAL_ONLY", "0") == "1"
            model = SentenceTransformer(requested_model, local_files_only=local_files_only)
            dimension_getter = getattr(model, "get_embedding_dimension", None) or getattr(
                model,
                "get_sentence_embedding_dimension",
            )
            dim = int(dimension_getter() or dimensions or DEFAULT_HASH_DIMENSIONS)
            self._model = model
            self._is_sentence_transformer = True
            self.info = EmbeddingRuntimeInfo(
                requested_backend=requested_backend,
                requested_model=requested_model,
                active_backend="sentence_transformers",
                active_model=requested_model,
                dimensions=dim,
            )
        except Exception as exc:  # pragma: no cover - exact loader failures depend on local env
            if not allow_fallback:
                raise
            self._use_hash_fallback(dimensions, f"{type(exc).__name__}: {exc}")

    def _use_hash_fallback(self, dimensions: int | None, reason: str) -> None:
        dim = dimensions or int(os.getenv("AI_COACH_HASH_EMBEDDING_DIM", str(DEFAULT_HASH_DIMENSIONS)))
        self._model = HashEmbeddingModel(dim)
        self.info = EmbeddingRuntimeInfo(
            requested_backend=self.requested_backend,
            requested_model=self.requested_model,
            active_backend="local_hash",
            active_model=DEFAULT_HASH_MODEL,
            dimensions=dim,
            is_fallback=True,
            fallback_reason=reason[:500],
        )

    @property
    def dimensions(self) -> int:
        return self.info.dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self._is_sentence_transformer:
            encoded = self._model.encode(  # type: ignore[attr-defined]
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [[float(value) for value in row] for row in encoded]
        return self._model.encode(texts)  # type: ignore[attr-defined]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def describe(self) -> dict[str, object]:
        return self.info.to_dict()


_ADAPTER_CACHE: dict[tuple[str | None, str | None, int | None, bool, bool | None], EmbeddingAdapter] = {}


def get_embedding_adapter(
    backend: str | None = None,
    model_name: str | None = None,
    dimensions: int | None = None,
    allow_fallback: bool = True,
    local_files_only: bool | None = None,
) -> EmbeddingAdapter:
    key = (backend, model_name, dimensions, allow_fallback, local_files_only)
    if key not in _ADAPTER_CACHE:
        _ADAPTER_CACHE[key] = EmbeddingAdapter(
            backend=backend,
            model_name=model_name,
            dimensions=dimensions,
            allow_fallback=allow_fallback,
            local_files_only=local_files_only,
        )
    return _ADAPTER_CACHE[key]
