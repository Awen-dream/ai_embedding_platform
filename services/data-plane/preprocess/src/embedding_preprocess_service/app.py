from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from embedding_platform_common.errors import PlatformError, error_payload
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import configure_logging, log_event
from embedding_preprocess_service.config import load_settings
from embedding_preprocess_service.domain.chunking import chunk_words, normalize_text
from embedding_preprocess_service.models import (
    PreprocessChunk,
    PreprocessRequest,
    PreprocessResponse,
)


def create_app() -> FastAPI:
    settings = load_settings()
    logger = configure_logging(settings.service_name)
    app = FastAPI(title="Embedding Preprocess Service", version="0.1.0")
    app.state.settings = settings
    app.state.logger = logger

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> JSONResponse:
        request.state.request_id = request.headers.get("x-request-id", generate_id("req"))
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        return response

    @app.exception_handler(PlatformError)
    async def handle_platform_error(request: Request, exc: PlatformError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_envelope(request.state.request_id).model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger,
            "preprocess.unexpected_error",
            request_id=request.state.request_id,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content=error_payload(
                request_id=request.state.request_id,
                code="SYS-INTERNAL-500001",
                message="unexpected internal error",
                error_type="internal_error",
            ),
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/internal/preprocess/text", response_model=PreprocessResponse)
    async def preprocess_text(request: Request, body: PreprocessRequest) -> PreprocessResponse:
        if not body.items:
            raise PlatformError(
                code="TASK-VAL-400001",
                message="items must not be empty",
                error_type="validation_error",
                status_code=400,
            )

        chunk_size_words = body.chunk_size_words or settings.default_chunk_size_words
        overlap_words = body.overlap_words if body.overlap_words is not None else settings.default_overlap_words

        chunks: list[PreprocessChunk] = []
        for item in body.items:
            normalized = normalize_text(item.text)
            if not normalized:
                continue
            words = normalized.split(" ")
            try:
                for start_word, end_word, chunk_tokens in chunk_words(words, chunk_size_words, overlap_words):
                    chunk_text = " ".join(chunk_tokens)
                    chunks.append(
                        PreprocessChunk(
                            chunk_id=generate_id("chunk"),
                            item_id=item.id,
                            text=chunk_text,
                            metadata=item.metadata,
                            start_word=start_word,
                            end_word=end_word,
                        )
                    )
            except ValueError as exc:
                raise PlatformError(
                    code="TASK-VAL-400001",
                    message=str(exc),
                    error_type="validation_error",
                    status_code=400,
                ) from exc

        log_event(
            logger,
            "embedding.preprocess.completed",
            request_id=request.state.request_id,
            tenant_id=body.tenant_id,
            input_count=len(body.items),
            chunk_count=len(chunks),
            duplicate_count=0,
        )
        return PreprocessResponse(
            request_id=request.state.request_id,
            input_count=len(body.items),
            chunk_count=len(chunks),
            duplicate_count=0,
            chunks=chunks,
        )

    return app


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "embedding_preprocess_service.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )

