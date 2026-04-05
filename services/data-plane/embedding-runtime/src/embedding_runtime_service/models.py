from __future__ import annotations

from typing import Any
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


class EmbeddingRequest(BaseModel):
    tenant_id: str
    model: str
    modality: str
    input: Union[str, list[str]]
    dimension: Optional[int] = None
    encoding_format: str = "float"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("modality")
    @classmethod
    def validate_modality(cls, value: str) -> str:
        if value != "text":
            raise ValueError("only text modality is supported in the MVP scaffold")
        return value


class EmbeddingItem(BaseModel):
    index: int
    embedding: list[float]


class Usage(BaseModel):
    input_tokens: int
    cache_hit: bool = False


class EmbeddingResponse(BaseModel):
    request_id: str
    model: str
    dimension: int
    data: list[EmbeddingItem]
    usage: Usage
