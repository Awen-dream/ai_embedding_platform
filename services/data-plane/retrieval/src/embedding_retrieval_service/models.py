from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RetrievalRequest(BaseModel):
    tenant_id: str
    index_id: str
    query: Optional[str] = None
    vector: Optional[list[float]] = None
    filters: dict[str, Any] = Field(default_factory=dict)
    top_k: int = 5


class RetrievalHit(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    request_id: str
    hits: list[RetrievalHit]

