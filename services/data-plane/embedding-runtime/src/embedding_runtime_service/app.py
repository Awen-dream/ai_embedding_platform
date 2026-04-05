from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from embedding_platform_common.errors import PlatformError, error_payload
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import configure_logging, log_event
from embedding_runtime_service.config import load_settings
from embedding_runtime_service.domain.encoder import estimate_input_tokens, stable_embedding
from embedding_runtime_service.models import EmbeddingItem, EmbeddingRequest, EmbeddingResponse, Usage


def create_app() -> FastAPI:
    settings = load_settings()
    logger = configure_logging(settings.service_name)
    app = FastAPI(title="Embedding Runtime Service", version="0.1.0")
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
            "embedding_runtime.unexpected_error",
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

    @app.post("/internal/embeddings", response_model=EmbeddingResponse)
    async def create_embeddings(request: Request, body: EmbeddingRequest) -> EmbeddingResponse:
        values = [body.input] if isinstance(body.input, str) else body.input
        if not values:
            raise PlatformError(
                code="EMB-VAL-400001",
                message="input is required",
                error_type="validation_error",
                status_code=400,
            )

        dimension = body.dimension or settings.default_dimension
        if dimension <= 0 or dimension > settings.max_dimension:
            raise PlatformError(
                code="VEC-VAL-400001",
                message=f"dimension must be between 1 and {settings.max_dimension}",
                error_type="validation_error",
                status_code=400,
            )

        items: list[EmbeddingItem] = []
        input_tokens = 0
        for index, value in enumerate(values):
            if not value.strip():
                raise PlatformError(
                    code="EMB-VAL-400001",
                    message="input is required",
                    error_type="validation_error",
                    status_code=400,
                )
            items.append(EmbeddingItem(index=index, embedding=stable_embedding(value, dimension)))
            input_tokens += estimate_input_tokens(value)

        log_event(
            logger,
            "embedding.runtime.completed",
            request_id=request.state.request_id,
            tenant_id=body.tenant_id,
            model=body.model,
            batch_size=len(values),
            dimension=dimension,
        )
        return EmbeddingResponse(
            request_id=request.state.request_id,
            model=body.model,
            dimension=dimension,
            data=items,
            usage=Usage(input_tokens=input_tokens, cache_hit=False),
        )

    return app


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "embedding_runtime_service.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )

