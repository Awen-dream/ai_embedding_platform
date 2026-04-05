from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class GatewaySettings:
    service_name: str = "gateway"
    host: str = "0.0.0.0"
    port: int = 8080
    api_key: str = "local-dev-key"
    auth_credentials_json: str = ""
    default_rate_limit_per_minute: int = 120
    runtime_url: str = "http://127.0.0.1:8082"
    task_orchestrator_url: str = "http://127.0.0.1:8081"
    retrieval_url: str = "http://127.0.0.1:8084"
    http_timeout_seconds: float = 5.0
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_seconds: float = 30.0


def load_settings() -> GatewaySettings:
    return GatewaySettings(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8080")),
        api_key=os.getenv("APP_API_KEY", "local-dev-key"),
        auth_credentials_json=os.getenv("APP_AUTH_CREDENTIALS_JSON", ""),
        default_rate_limit_per_minute=int(os.getenv("APP_DEFAULT_RATE_LIMIT_PER_MINUTE", "120")),
        runtime_url=os.getenv("APP_RUNTIME_URL", "http://127.0.0.1:8082"),
        task_orchestrator_url=os.getenv("APP_TASK_ORCHESTRATOR_URL", "http://127.0.0.1:8081"),
        retrieval_url=os.getenv("APP_RETRIEVAL_URL", "http://127.0.0.1:8084"),
        http_timeout_seconds=float(os.getenv("APP_HTTP_TIMEOUT_SECONDS", "5")),
        circuit_breaker_failure_threshold=int(os.getenv("APP_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3")),
        circuit_breaker_recovery_seconds=float(os.getenv("APP_CIRCUIT_BREAKER_RECOVERY_SECONDS", "30")),
    )
