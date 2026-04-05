from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock

from embedding_platform_common.errors import PlatformError
from embedding_vector_store_proxy.domain.search import cosine_similarity, matches_filters
from embedding_vector_store_proxy.models import SearchHit, VectorItem


@dataclass
class IndexState:
    dimension: int
    items: dict[str, VectorItem] = field(default_factory=dict)


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._indexes: dict[tuple[str, str], IndexState] = {}
        self._lock = Lock()

    def upsert(self, tenant_id: str, index_id: str, items: list[VectorItem]) -> int:
        if not items:
            return 0

        dimension = len(items[0].vector)
        if dimension == 0:
            raise PlatformError(
                code="VEC-VAL-400001",
                message="vector dimension must be greater than zero",
                error_type="validation_error",
                status_code=400,
            )

        with self._lock:
            key = (tenant_id, index_id)
            state = self._indexes.get(key)
            if state is None:
                state = IndexState(dimension=dimension)
                self._indexes[key] = state
            elif state.dimension != dimension:
                raise PlatformError(
                    code="VEC-VAL-400001",
                    message="vector dimension does not match existing index",
                    error_type="validation_error",
                    status_code=400,
                )

            for item in items:
                if len(item.vector) != state.dimension:
                    raise PlatformError(
                        code="VEC-VAL-400001",
                        message="vector dimension does not match existing index",
                        error_type="validation_error",
                        status_code=400,
                    )
                state.items[item.id] = item

            return state.dimension

    def search(
        self,
        tenant_id: str,
        index_id: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, object],
    ) -> tuple[int, list[SearchHit]]:
        with self._lock:
            state = self._indexes.get((tenant_id, index_id))
            if state is None:
                raise PlatformError(
                    code="VEC-NOTFOUND-404001",
                    message="index not found",
                    error_type="not_found_error",
                    status_code=404,
                )

            if len(vector) != state.dimension:
                raise PlatformError(
                    code="VEC-VAL-400001",
                    message="query vector dimension does not match index dimension",
                    error_type="validation_error",
                    status_code=400,
                )

            hits: list[SearchHit] = []
            for item in state.items.values():
                if not matches_filters(item.metadata, filters):
                    continue
                score = round(cosine_similarity(vector, item.vector), 6)
                hits.append(SearchHit(id=item.id, score=score, metadata=item.metadata))

            hits.sort(key=lambda hit: hit.score, reverse=True)
            return state.dimension, hits[:top_k]

