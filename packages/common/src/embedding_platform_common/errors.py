from __future__ import annotations

from typing import Any
from typing import Optional

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    type: str
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    request_id: str
    error: ErrorBody


class PlatformError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        error_type: str,
        status_code: int,
        retryable: bool = False,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.retryable = retryable
        self.details = details or {}

    def to_envelope(self, request_id: str) -> ErrorEnvelope:
        return ErrorEnvelope(
            request_id=request_id,
            error=ErrorBody(
                code=self.code,
                message=self.message,
                type=self.error_type,
                retryable=self.retryable,
                details=self.details,
            ),
        )


def error_payload(
    *,
    request_id: str,
    code: str,
    message: str,
    error_type: str,
    retryable: bool = False,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return ErrorEnvelope(
        request_id=request_id,
        error=ErrorBody(
            code=code,
            message=message,
            type=error_type,
            retryable=retryable,
            details=details or {},
        ),
    ).model_dump()
