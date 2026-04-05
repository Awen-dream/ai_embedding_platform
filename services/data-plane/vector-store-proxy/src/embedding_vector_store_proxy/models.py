from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class VectorItem(BaseModel):
    id: str
    vector: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpsertVectorsRequest(BaseModel):
    tenant_id: str
    index_id: str
    items: list[VectorItem]


class UpsertVectorsResponse(BaseModel):
    request_id: str
    index_id: str
    upserted_count: int
    dimension: int


class SearchRequest(BaseModel):
    tenant_id: str
    index_id: str
    vector: list[float]
    top_k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchHit(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    request_id: str
    hits: list[SearchHit]
    dimension: Optional[int] = None

