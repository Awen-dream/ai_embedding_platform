from __future__ import annotations

from typing import Any
from typing import Optional

import httpx

from embedding_platform_common.errors import PlatformError
from embedding_gateway.internal.circuit_breaker import CircuitBreakerRegistry


async def forward_request(
    *,
    method: str,
    url: str,
    downstream_name: str,
    request_id: str,
    timeout: float,
    payload: Optional[dict[str, Any]] = None,
    extra_headers: Optional[dict[str, str]] = None,
    circuit_breaker: Optional[CircuitBreakerRegistry] = None,
) -> tuple[int, dict[str, Any]]:
    if circuit_breaker is not None:
        circuit_breaker.before_request(downstream_name)

    headers = {"x-request-id": request_id}
    if extra_headers:
        headers.update(extra_headers)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(method, url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            if circuit_breaker is not None:
                circuit_breaker.record_failure(downstream_name)
            raise PlatformError(
                code="SYS-TIMEOUT-504001",
                message="downstream request timed out",
                error_type="timeout_error",
                status_code=504,
                retryable=True,
                details={"target": url},
            ) from exc
        except httpx.HTTPError as exc:
            if circuit_breaker is not None:
                circuit_breaker.record_failure(downstream_name)
            raise PlatformError(
                code="SYS-DEP-502001",
                message="downstream service is unavailable",
                error_type="dependency_error",
                status_code=502,
                retryable=True,
                details={"target": url},
            ) from exc

    if circuit_breaker is not None:
        if response.status_code >= 500:
            circuit_breaker.record_failure(downstream_name)
        else:
            circuit_breaker.record_success(downstream_name)

    try:
        data = response.json()
    except ValueError:
        data = {"raw_body": response.text}

    return response.status_code, data
