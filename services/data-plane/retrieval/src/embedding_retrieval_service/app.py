from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
import uvicorn

from embedding_platform_common.errors import PlatformError, error_payload
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import configure_logging, log_event
from embedding_retrieval_service.config import load_settings
from embedding_retrieval_service.domain.validation import has_query_or_vector
from embedding_retrieval_service.models import RetrievalHit, RetrievalRequest, RetrievalResponse


def create_app() -> FastAPI:
    settings = load_settings()
    logger = configure_logging(settings.service_name)
    app = FastAPI(title="Embedding Retrieval Service", version="0.1.0")
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
            "retrieval.unexpected_error",
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

    @app.post("/internal/retrieval/search", response_model=RetrievalResponse)
    async def retrieval_search(request: Request, body: RetrievalRequest) -> RetrievalResponse:
        if body.top_k <= 0:
            raise PlatformError(
                code="RET-VAL-400001",
                message="top_k must be greater than zero",
                error_type="validation_error",
                status_code=400,
            )
        if not has_query_or_vector(body.query, body.vector):
            raise PlatformError(
                code="RET-VAL-400002",
                message="query or vector is required",
                error_type="validation_error",
                status_code=400,
            )

        query_vector = body.vector
        if query_vector is None:
            query_vector = await embed_query(
                request_id=request.state.request_id,
                settings=settings,
                tenant_id=body.tenant_id,
                query=body.query or "",
            )

        hits = await search_vector_store(
            request_id=request.state.request_id,
            settings=settings,
            tenant_id=body.tenant_id,
            index_id=body.index_id,
            vector=query_vector,
            top_k=body.top_k,
            filters=body.filters,
        )
        log_event(
            logger,
            "retrieval.search.completed",
            request_id=request.state.request_id,
            tenant_id=body.tenant_id,
            index_id=body.index_id,
            hit_count=len(hits),
        )
        return RetrievalResponse(
            request_id=request.state.request_id,
            hits=[RetrievalHit(**hit) for hit in hits],
        )

    return app


async def embed_query(
    *,
    request_id: str,
    settings: Any,
    tenant_id: str,
    query: str,
) -> list[float]:
    payload = {
        "tenant_id": tenant_id,
        "model": settings.default_model,
        "modality": "text",
        "input": [query],
        "dimension": settings.default_dimension,
    }
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        response = await client.post(
            f"{settings.runtime_url}/internal/embeddings",
            json=payload,
            headers={"x-request-id": request_id},
        )
    data = _parse_response(response)
    return data["data"][0]["embedding"]


async def search_vector_store(
    *,
    request_id: str,
    settings: Any,
    tenant_id: str,
    index_id: str,
    vector: list[float],
    top_k: int,
    filters: dict[str, object],
) -> list[dict[str, Any]]:
    payload = {
        "tenant_id": tenant_id,
        "index_id": index_id,
        "vector": vector,
        "top_k": top_k,
        "filters": filters,
    }
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        response = await client.post(
            f"{settings.vector_store_url}/internal/search",
            json=payload,
            headers={"x-request-id": request_id},
        )
    data = _parse_response(response)
    return data["hits"]


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise PlatformError(
            code="SYS-DEP-502001",
            message="downstream response is not valid json",
            error_type="dependency_error",
            status_code=502,
            retryable=True,
        ) from exc

    if response.status_code >= 400:
        error = data.get("error", {})
        raise PlatformError(
            code=error.get("code", "SYS-DEP-502001"),
            message=error.get("message", "downstream service error"),
            error_type=error.get("type", "dependency_error"),
            status_code=response.status_code,
            retryable=error.get("retryable", response.status_code >= 500),
            details=error.get("details", {}),
        )
    return data


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "embedding_retrieval_service.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )

