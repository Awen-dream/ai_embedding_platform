from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from embedding_platform_common.auth import is_api_key_valid
from embedding_platform_common.errors import PlatformError, error_payload
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import configure_logging, log_event
from embedding_gateway.config import GatewaySettings, load_settings
from embedding_gateway.internal.proxy import forward_request


def create_app() -> FastAPI:
    settings = load_settings()
    logger = configure_logging(settings.service_name)
    app = FastAPI(title="Embedding Platform Gateway", version="0.1.0")
    app.state.settings = settings
    app.state.logger = logger

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> JSONResponse:
        request_id = request.headers.get("x-request-id", generate_id("req"))
        request.state.request_id = request_id
        request.state.logger = logger

        if request.url.path.startswith("/v1/"):
            api_key = request.headers.get("x-api-key")
            if not is_api_key_valid(settings.api_key, api_key):
                return JSONResponse(
                    status_code=401,
                    content=error_payload(
                        request_id=request_id,
                        code="AUTH-AUTHN-401002",
                        message="invalid api key",
                        error_type="authentication_error",
                    ),
                )

        response = await call_next(request)
        response.headers["x-request-id"] = request_id
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
            "gateway.unexpected_error",
            request_id=request.state.request_id,
            path=request.url.path,
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

    @app.post("/v1/embeddings")
    async def create_embeddings(request: Request) -> JSONResponse:
        payload = await request.json()
        status_code, data = await forward_request(
            method="POST",
            url=f"{settings.runtime_url}/internal/embeddings",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
            payload=payload,
        )
        log_event(
            logger,
            "gateway.embedding.forwarded",
            request_id=request.state.request_id,
            status_code=status_code,
        )
        return JSONResponse(status_code=status_code, content=data)

    @app.post("/v1/tasks/embedding")
    async def create_embedding_task(request: Request) -> JSONResponse:
        payload = await request.json()
        status_code, data = await forward_request(
            method="POST",
            url=f"{settings.task_orchestrator_url}/internal/tasks/embedding",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
            payload=payload,
        )
        log_event(
            logger,
            "gateway.task.forwarded",
            request_id=request.state.request_id,
            status_code=status_code,
        )
        return JSONResponse(status_code=status_code, content=data)

    @app.get("/v1/tasks/{task_id}")
    async def get_task(task_id: str, request: Request) -> JSONResponse:
        status_code, data = await forward_request(
            method="GET",
            url=f"{settings.task_orchestrator_url}/internal/tasks/{task_id}",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
        )
        return JSONResponse(status_code=status_code, content=data)

    @app.post("/v1/retrieval/search")
    async def retrieval_search(request: Request) -> JSONResponse:
        payload = await request.json()
        status_code, data = await forward_request(
            method="POST",
            url=f"{settings.retrieval_url}/internal/retrieval/search",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
            payload=payload,
        )
        return JSONResponse(status_code=status_code, content=data)

    return app


def main() -> None:
    settings = load_settings()
    uvicorn.run("embedding_gateway.app:create_app", factory=True, host=settings.host, port=settings.port)
