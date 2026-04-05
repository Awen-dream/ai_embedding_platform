from __future__ import annotations

from typing import Any
from typing import Optional

from pydantic import BaseModel, Field


class PreprocessItem(BaseModel):
    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreprocessRequest(BaseModel):
    tenant_id: str
    items: list[PreprocessItem]
    chunk_size_words: Optional[int] = None
    overlap_words: Optional[int] = None


class PreprocessChunk(BaseModel):
    chunk_id: str
    item_id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    start_word: int
    end_word: int


class PreprocessResponse(BaseModel):
    request_id: str
    input_count: int
    chunk_count: int
    duplicate_count: int = 0
    chunks: list[PreprocessChunk]

