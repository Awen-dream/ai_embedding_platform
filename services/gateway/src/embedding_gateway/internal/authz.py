from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from embedding_gateway.config import GatewaySettings


@dataclass(frozen=True)
class AuthCredential:
    """Gateway credential model with tenant scope and optional per-key rate limit."""

    name: str
    api_key: str
    tenant_ids: set[str]
    rate_limit_per_minute: Optional[int] = None

    def allows_tenant(self, tenant_id: Optional[str]) -> bool:
        """Return whether the credential can be used for the provided tenant."""
        if not self.tenant_ids:
            return True
        return tenant_id in self.tenant_ids

    def resolve_tenant(self, tenant_id: Optional[str]) -> Optional[str]:
        """Infer tenant_id when the credential is bound to exactly one tenant."""
        if tenant_id:
            return tenant_id
        if len(self.tenant_ids) == 1:
            return next(iter(self.tenant_ids))
        return None


class CredentialRegistry:
    """In-memory lookup table for API key to credential resolution."""

    def __init__(self, credentials: list[AuthCredential]) -> None:
        self._credentials = {credential.api_key: credential for credential in credentials}

    def resolve(self, api_key: Optional[str]) -> Optional[AuthCredential]:
        """Resolve a credential by API key, returning None when the key is unknown."""
        if not api_key:
            return None
        return self._credentials.get(api_key)


def load_credential_registry(settings: GatewaySettings) -> CredentialRegistry:
    """Build the credential registry from JSON config or the legacy single API key."""
    credentials: list[AuthCredential] = []
    if settings.auth_credentials_json:
        raw = json.loads(settings.auth_credentials_json)
        if not isinstance(raw, list):
            raise ValueError("APP_AUTH_CREDENTIALS_JSON must be a JSON array")
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                raise ValueError(f"credential at index {index} must be an object")
            credentials.append(
                AuthCredential(
                    name=str(item.get("name") or f"credential-{index}"),
                    api_key=str(item["api_key"]),
                    tenant_ids={str(value) for value in item.get("tenant_ids", [])},
                    rate_limit_per_minute=_optional_int(item.get("rate_limit_per_minute")),
                )
            )
    elif settings.api_key:
        credentials.append(
            AuthCredential(
                name="legacy-default",
                api_key=settings.api_key,
                tenant_ids=set(),
                rate_limit_per_minute=settings.default_rate_limit_per_minute,
            )
        )
    return CredentialRegistry(credentials)


def extract_tenant_id(method: str, headers: dict[str, str], body: Optional[Any]) -> Optional[str]:
    """Extract tenant_id from headers first, then from JSON payload for write requests."""
    tenant_id = headers.get("x-tenant-id")
    if tenant_id:
        return tenant_id
    if method.upper() in {"POST", "PUT", "PATCH"} and isinstance(body, dict):
        raw = body.get("tenant_id")
        if raw is not None:
            return str(raw)
    return None


def _optional_int(value: Any) -> Optional[int]:
    """Convert optional config values to int while preserving None."""
    if value is None:
        return None
    return int(value)
