from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from embedding_platform_common.errors import PlatformError
from embedding_runtime_service.config import EmbeddingRuntimeSettings
from embedding_runtime_service.domain.encoder import estimate_input_tokens, stable_embedding


@dataclass(frozen=True)
class EmbeddingBatch:
    """Normalized embedding provider result returned to the runtime service."""

    vectors: list[list[float]]
    input_tokens: int
    provider: str


class EmbeddingProvider(Protocol):
    """Provider interface implemented by concrete embedding backends."""

    async def embed(
        self,
        *,
        texts: list[str],
        model: str,
        dimension: int,
        encoding_format: str,
        metadata: dict[str, Any],
        request_id: str,
        tenant_id: str,
    ) -> EmbeddingBatch:
        """Generate vectors for a batch of texts and return normalized usage data."""
        ...


class HashingEmbeddingProvider:
    """Deterministic local provider for development, tests, and offline fallback."""

    async def embed(
        self,
        *,
        texts: list[str],
        model: str,
        dimension: int,
        encoding_format: str,
        metadata: dict[str, Any],
        request_id: str,
        tenant_id: str,
    ) -> EmbeddingBatch:
        return EmbeddingBatch(
            vectors=[stable_embedding(text, dimension) for text in texts],
            input_tokens=sum(estimate_input_tokens(text) for text in texts),
            provider="hashing",
        )


class OpenAICompatibleEmbeddingProvider:
    """HTTP provider for OpenAI-compatible `/embeddings` APIs."""

    def __init__(self, *, base_url: str, api_key: str, path: str, timeout: float) -> None:
        if not base_url:
            raise PlatformError(
                code="SYS-INTERNAL-500001",
                message="openai_compatible backend requires APP_EMBEDDING_API_BASE_URL",
                error_type="internal_error",
                status_code=500,
            )
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._path = path if path.startswith("/") else f"/{path}"
        self._timeout = timeout

    async def embed(
        self,
        *,
        texts: list[str],
        model: str,
        dimension: int,
        encoding_format: str,
        metadata: dict[str, Any],
        request_id: str,
        tenant_id: str,
    ) -> EmbeddingBatch:
        """Call a remote embeddings endpoint and normalize its response shape."""
        payload: dict[str, Any] = {
            "model": model,
            "input": texts,
            "encoding_format": encoding_format,
        }
        if dimension > 0:
            payload["dimensions"] = dimension
        headers = {"x-request-id": request_id}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}{self._path}",
                    json=payload,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                raise PlatformError(
                    code="SYS-TIMEOUT-504001",
                    message="embedding provider timed out",
                    error_type="timeout_error",
                    status_code=504,
                    retryable=True,
                    details={"target": self._base_url},
                ) from exc
            except httpx.HTTPError as exc:
                raise PlatformError(
                    code="SYS-DEP-502001",
                    message="embedding provider is unavailable",
                    error_type="dependency_error",
                    status_code=502,
                    retryable=True,
                    details={"target": self._base_url},
                ) from exc

        data = _parse_provider_response(response)
        vectors = [list(row["embedding"]) for row in data.get("data", [])]
        if len(vectors) != len(texts):
            raise PlatformError(
                code="SYS-DEP-502001",
                message="embedding provider returned unexpected vector count",
                error_type="dependency_error",
                status_code=502,
                retryable=True,
            )
        usage = data.get("usage", {})
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        if input_tokens <= 0:
            input_tokens = sum(estimate_input_tokens(text) for text in texts)
        return EmbeddingBatch(
            vectors=vectors,
            input_tokens=input_tokens,
            provider="openai_compatible",
        )


def build_embedding_provider(settings: EmbeddingRuntimeSettings) -> EmbeddingProvider:
    """Instantiate the configured embedding provider backend."""
    backend = settings.embedding_backend.lower()
    if backend == "hashing":
        return HashingEmbeddingProvider()
    if backend == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding_api_base_url,
            api_key=settings.embedding_api_key,
            path=settings.embedding_api_path,
            timeout=settings.http_timeout_seconds,
        )
    raise PlatformError(
        code="SYS-INTERNAL-500001",
        message=f"unsupported embedding backend: {settings.embedding_backend}",
        error_type="internal_error",
        status_code=500,
    )


def _parse_provider_response(response: httpx.Response) -> dict[str, Any]:
    """Validate the provider response and normalize downstream errors."""
    try:
        data = response.json()
    except ValueError as exc:
        raise PlatformError(
            code="SYS-DEP-502001",
            message="embedding provider returned invalid json",
            error_type="dependency_error",
            status_code=502,
            retryable=True,
        ) from exc

    if response.status_code >= 400:
        message = "embedding provider error"
        if isinstance(data, dict):
            error = data.get("error", {})
            if isinstance(error, dict):
                message = str(error.get("message") or message)
        raise PlatformError(
            code="SYS-DEP-502001",
            message=message,
            error_type="dependency_error",
            status_code=response.status_code,
            retryable=response.status_code >= 500,
            details={"provider_status_code": response.status_code},
        )
    return data
