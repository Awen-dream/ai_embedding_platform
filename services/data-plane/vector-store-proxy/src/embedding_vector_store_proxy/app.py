from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from embedding_platform_common.errors import PlatformError, error_payload
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import configure_logging, log_event
from embedding_vector_store_proxy.config import load_settings
from embedding_vector_store_proxy.models import (
    SearchRequest,
    SearchResponse,
    UpsertVectorsRequest,
    UpsertVectorsResponse,
)
from embedding_vector_store_proxy.store import InMemoryVectorStore


def create_app() -> FastAPI:
    settings = load_settings()
    logger = configure_logging(settings.service_name)
    store = InMemoryVectorStore()
    app = FastAPI(title="Embedding Vector Store Proxy", version="0.1.0")
    app.state.store = store
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
            "vector_store_proxy.unexpected_error",
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

    @app.post("/internal/vectors/upsert", response_model=UpsertVectorsResponse)
    async def upsert_vectors(request: Request, body: UpsertVectorsRequest) -> UpsertVectorsResponse:
        dimension = store.upsert(body.tenant_id, body.index_id, body.items)
        log_event(
            logger,
            "embedding.vector.upserted",
            request_id=request.state.request_id,
            tenant_id=body.tenant_id,
            index_id=body.index_id,
            upserted_count=len(body.items),
        )
        return UpsertVectorsResponse(
            request_id=request.state.request_id,
            index_id=body.index_id,
            upserted_count=len(body.items),
            dimension=dimension,
        )

    @app.post("/internal/search", response_model=SearchResponse)
    async def search_vectors(request: Request, body: SearchRequest) -> SearchResponse:
        if body.top_k <= 0:
            raise PlatformError(
                code="RET-VAL-400001",
                message="top_k must be greater than zero",
                error_type="validation_error",
                status_code=400,
            )
        dimension, hits = store.search(body.tenant_id, body.index_id, body.vector, body.top_k, body.filters)
        return SearchResponse(request_id=request.state.request_id, hits=hits, dimension=dimension)

    return app


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "embedding_vector_store_proxy.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )

