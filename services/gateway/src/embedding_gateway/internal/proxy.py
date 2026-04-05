from __future__ import annotations

from typing import Any
from typing import Optional

import httpx

from embedding_platform_common.errors import PlatformError


async def forward_request(
    *,
    method: str,
    url: str,
    request_id: str,
    timeout: float,
    payload: Optional[dict[str, Any]] = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"x-request-id": request_id}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(method, url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise PlatformError(
                code="SYS-TIMEOUT-504001",
                message="downstream request timed out",
                error_type="timeout_error",
                status_code=504,
                retryable=True,
                details={"target": url},
            ) from exc
        except httpx.HTTPError as exc:
            raise PlatformError(
                code="SYS-DEP-502001",
                message="downstream service is unavailable",
                error_type="dependency_error",
                status_code=502,
                retryable=True,
                details={"target": url},
            ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {"raw_body": response.text}

    return response.status_code, data
