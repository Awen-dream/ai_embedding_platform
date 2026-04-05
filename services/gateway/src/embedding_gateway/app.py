from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from embedding_platform_common.errors import PlatformError, error_payload
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import configure_logging, log_event
from embedding_gateway.config import GatewaySettings, load_settings
from embedding_gateway.internal.authz import extract_tenant_id, load_credential_registry
from embedding_gateway.internal.circuit_breaker import CircuitBreakerRegistry
from embedding_gateway.internal.proxy import forward_request
from embedding_gateway.internal.rate_limit import TokenBucketRateLimiter


def create_app() -> FastAPI:
    settings = load_settings()
    logger = configure_logging(settings.service_name)
    credentials = load_credential_registry(settings)
    rate_limiter = TokenBucketRateLimiter()
    circuit_breaker = CircuitBreakerRegistry(
        failure_threshold=settings.circuit_breaker_failure_threshold,
        recovery_seconds=settings.circuit_breaker_recovery_seconds,
    )
    app = FastAPI(title="Embedding Platform Gateway", version="0.1.0")
    app.state.settings = settings
    app.state.logger = logger
    app.state.credentials = credentials
    app.state.rate_limiter = rate_limiter
    app.state.circuit_breaker = circuit_breaker

    @app.middleware("http")
    async def request_context(request: Request, call_next: Any) -> JSONResponse:
        request_id = request.headers.get("x-request-id", generate_id("req"))
        request.state.request_id = request_id
        request.state.logger = logger

        if request.url.path.startswith("/v1/"):
            api_key = request.headers.get("x-api-key")
            body: Any = None
            if request.method.upper() in {"POST", "PUT", "PATCH"}:
                try:
                    body = await request.json()
                    request.state.request_body = body
                except ValueError:
                    body = None

            credential = credentials.resolve(api_key)
            if credential is None:
                return JSONResponse(
                    status_code=401,
                    content=error_payload(
                        request_id=request_id,
                        code="AUTH-AUTHN-401002",
                        message="invalid api key",
                        error_type="authentication_error",
                    ),
                )
            tenant_id = credential.resolve_tenant(extract_tenant_id(request.method, dict(request.headers), body))
            if credential.tenant_ids and tenant_id is None:
                return JSONResponse(
                    status_code=400,
                    content=error_payload(
                        request_id=request_id,
                        code="AUTH-AUTHZ-400001",
                        message="tenant context is required for this credential",
                        error_type="validation_error",
                    ),
                )
            if not credential.allows_tenant(tenant_id):
                return JSONResponse(
                    status_code=403,
                    content=error_payload(
                        request_id=request_id,
                        code="AUTH-AUTHZ-403001",
                        message="credential is not allowed for the requested tenant",
                        error_type="authorization_error",
                    ),
                )
            limit = credential.rate_limit_per_minute or settings.default_rate_limit_per_minute
            if not rate_limiter.allow(f"{credential.name}:{tenant_id or 'global'}", limit):
                return JSONResponse(
                    status_code=429,
                    content=error_payload(
                        request_id=request_id,
                        code="SYS-RATELIMIT-429001",
                        message="rate limit exceeded",
                        error_type="rate_limit_error",
                        retryable=True,
                    ),
                )
            request.state.credential = credential
            request.state.tenant_id = tenant_id

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
        payload = await _get_request_payload(request)
        status_code, data = await forward_request(
            method="POST",
            url=f"{settings.runtime_url}/internal/embeddings",
            downstream_name="embedding-runtime",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
            payload=payload,
            extra_headers=_downstream_headers(request),
            circuit_breaker=circuit_breaker,
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
        payload = await _get_request_payload(request)
        status_code, data = await forward_request(
            method="POST",
            url=f"{settings.task_orchestrator_url}/internal/tasks/embedding",
            downstream_name="task-orchestrator",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
            payload=payload,
            extra_headers=_downstream_headers(request),
            circuit_breaker=circuit_breaker,
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
            downstream_name="task-orchestrator",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
            extra_headers=_downstream_headers(request),
            circuit_breaker=circuit_breaker,
        )
        return JSONResponse(status_code=status_code, content=data)

    @app.post("/v1/retrieval/search")
    async def retrieval_search(request: Request) -> JSONResponse:
        payload = await _get_request_payload(request)
        status_code, data = await forward_request(
            method="POST",
            url=f"{settings.retrieval_url}/internal/retrieval/search",
            downstream_name="retrieval",
            request_id=request.state.request_id,
            timeout=settings.http_timeout_seconds,
            payload=payload,
            extra_headers=_downstream_headers(request),
            circuit_breaker=circuit_breaker,
        )
        return JSONResponse(status_code=status_code, content=data)

    return app


def _downstream_headers(request: Request) -> dict[str, str]:
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        return {"x-tenant-id": tenant_id}
    return {}


async def _get_request_payload(request: Request) -> Any:
    if hasattr(request.state, "request_body"):
        return request.state.request_body
    return await request.json()


def main() -> None:
    settings = load_settings()
    uvicorn.run("embedding_gateway.app:create_app", factory=True, host=settings.host, port=settings.port)
