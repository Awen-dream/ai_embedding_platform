from __future__ import annotations

from typing import Union

from embedding_platform_common.errors import PlatformError
from embedding_vector_store_proxy.config import VectorStoreProxySettings
from embedding_vector_store_proxy.store import InMemoryVectorStore, SqliteVectorStore


def create_vector_store(settings: VectorStoreProxySettings) -> Union[InMemoryVectorStore, SqliteVectorStore]:
    """Create the vector store implementation selected by configuration."""
    backend = settings.store_backend.lower()
    if backend == "inmemory":
        return InMemoryVectorStore()
    if backend == "sqlite":
        return SqliteVectorStore(path=settings.sqlite_path)
    raise PlatformError(
        code="SYS-INTERNAL-500001",
        message=f"unsupported vector store backend: {settings.store_backend}",
        error_type="internal_error",
        status_code=500,
    )
