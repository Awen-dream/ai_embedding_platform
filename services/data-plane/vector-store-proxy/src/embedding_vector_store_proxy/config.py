from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class VectorStoreProxySettings:
    service_name: str = "vector-store-proxy"
    host: str = "0.0.0.0"
    port: int = 8083
    store_backend: str = "sqlite"
    sqlite_path: str = ".data/vector-store.db"


def load_settings() -> VectorStoreProxySettings:
    return VectorStoreProxySettings(
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8083")),
        store_backend=os.getenv("APP_STORE_BACKEND", "sqlite"),
        sqlite_path=os.getenv("APP_SQLITE_PATH", ".data/vector-store.db"),
    )
