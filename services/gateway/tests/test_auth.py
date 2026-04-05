import unittest

from embedding_gateway.config import GatewaySettings
from embedding_gateway.internal.authz import extract_tenant_id, load_credential_registry
from embedding_gateway.internal.circuit_breaker import CircuitBreakerRegistry
from embedding_gateway.internal.rate_limit import TokenBucketRateLimiter


class AuthHelpersTest(unittest.TestCase):
    def test_registry_supports_legacy_api_key(self) -> None:
        registry = load_credential_registry(GatewaySettings(api_key="local-dev-key"))
        self.assertIsNotNone(registry.resolve("local-dev-key"))

    def test_registry_supports_tenant_scoped_credentials(self) -> None:
        registry = load_credential_registry(
            GatewaySettings(
                api_key="",
                auth_credentials_json='[{"name":"tenant-a","api_key":"tenant-a-key","tenant_ids":["tenant-a"]}]',
            )
        )
        credential = registry.resolve("tenant-a-key")
        self.assertIsNotNone(credential)
        self.assertTrue(credential.allows_tenant("tenant-a"))
        self.assertFalse(credential.allows_tenant("tenant-b"))

    def test_extract_tenant_id_prefers_header_then_body(self) -> None:
        self.assertEqual(extract_tenant_id("POST", {"x-tenant-id": "tenant-h"}, {"tenant_id": "tenant-b"}), "tenant-h")
        self.assertEqual(extract_tenant_id("POST", {}, {"tenant_id": "tenant-b"}), "tenant-b")

    def test_rate_limiter_rejects_when_capacity_is_exhausted(self) -> None:
        limiter = TokenBucketRateLimiter()
        self.assertTrue(limiter.allow("tenant-a", 1))
        self.assertFalse(limiter.allow("tenant-a", 1))

    def test_circuit_breaker_opens_after_threshold(self) -> None:
        breaker = CircuitBreakerRegistry(failure_threshold=2, recovery_seconds=60)
        breaker.record_failure("runtime")
        breaker.record_failure("runtime")
        with self.assertRaises(Exception):
            breaker.before_request("runtime")
