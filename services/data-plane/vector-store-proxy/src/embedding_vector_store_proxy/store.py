from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import sqlite3
from threading import Lock

from embedding_platform_common.errors import PlatformError
from embedding_vector_store_proxy.domain.search import cosine_similarity, matches_filters
from embedding_vector_store_proxy.models import SearchHit, VectorItem


@dataclass
class IndexState:
    """In-memory index snapshot for one `(tenant_id, index_id)` pair."""

    dimension: int
    items: dict[str, VectorItem] = field(default_factory=dict)


class InMemoryVectorStore:
    """Ephemeral vector store implementation used by tests and scaffold mode."""

    def __init__(self) -> None:
        self._indexes: dict[tuple[str, str], IndexState] = {}
        self._lock = Lock()

    def upsert(self, tenant_id: str, index_id: str, items: list[VectorItem]) -> int:
        """Insert or update vectors in the named in-memory index."""
        if not items:
            return 0

        dimension = len(items[0].vector)
        if dimension == 0:
            raise PlatformError(
                code="VEC-VAL-400001",
                message="vector dimension must be greater than zero",
                error_type="validation_error",
                status_code=400,
            )

        with self._lock:
            key = (tenant_id, index_id)
            state = self._indexes.get(key)
            if state is None:
                state = IndexState(dimension=dimension)
                self._indexes[key] = state
            elif state.dimension != dimension:
                raise PlatformError(
                    code="VEC-VAL-400001",
                    message="vector dimension does not match existing index",
                    error_type="validation_error",
                    status_code=400,
                )

            for item in items:
                if len(item.vector) != state.dimension:
                    raise PlatformError(
                        code="VEC-VAL-400001",
                        message="vector dimension does not match existing index",
                        error_type="validation_error",
                        status_code=400,
                    )
                state.items[item.id] = item

            return state.dimension

    def search(
        self,
        tenant_id: str,
        index_id: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, object],
    ) -> tuple[int, list[SearchHit]]:
        """Search the in-memory index with cosine similarity and exact metadata filters."""
        with self._lock:
            state = self._indexes.get((tenant_id, index_id))
            if state is None:
                raise PlatformError(
                    code="VEC-NOTFOUND-404001",
                    message="index not found",
                    error_type="not_found_error",
                    status_code=404,
                )

            if len(vector) != state.dimension:
                raise PlatformError(
                    code="VEC-VAL-400001",
                    message="query vector dimension does not match index dimension",
                    error_type="validation_error",
                    status_code=400,
                )

            hits: list[SearchHit] = []
            for item in state.items.values():
                if not matches_filters(item.metadata, filters):
                    continue
                score = round(cosine_similarity(vector, item.vector), 6)
                hits.append(SearchHit(id=item.id, score=score, metadata=item.metadata))

            hits.sort(key=lambda hit: hit.score, reverse=True)
            return state.dimension, hits[:top_k]


class SqliteVectorStore:
    """Single-node durable vector store backed by SQLite tables."""

    def __init__(self, *, path: str) -> None:
        self._lock = Lock()
        self._conn = self._connect(path)
        self._initialize()

    def upsert(self, tenant_id: str, index_id: str, items: list[VectorItem]) -> int:
        """Insert or update vectors while enforcing a stable dimension per index."""
        if not items:
            return 0

        dimension = len(items[0].vector)
        if dimension == 0:
            raise PlatformError(
                code="VEC-VAL-400001",
                message="vector dimension must be greater than zero",
                error_type="validation_error",
                status_code=400,
            )

        with self._lock:
            row = self._conn.execute(
                "SELECT dimension FROM indexes WHERE tenant_id = ? AND index_id = ?",
                (tenant_id, index_id),
            ).fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO indexes (tenant_id, index_id, dimension) VALUES (?, ?, ?)",
                    (tenant_id, index_id, dimension),
                )
            elif int(row["dimension"]) != dimension:
                raise PlatformError(
                    code="VEC-VAL-400001",
                    message="vector dimension does not match existing index",
                    error_type="validation_error",
                    status_code=400,
                )

            for item in items:
                if len(item.vector) != dimension:
                    raise PlatformError(
                        code="VEC-VAL-400001",
                        message="vector dimension does not match existing index",
                        error_type="validation_error",
                        status_code=400,
                    )
                self._conn.execute(
                    """
                    INSERT INTO vectors (tenant_id, index_id, item_id, dimension, vector_json, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tenant_id, index_id, item_id)
                    DO UPDATE SET
                        dimension = excluded.dimension,
                        vector_json = excluded.vector_json,
                        metadata_json = excluded.metadata_json
                    """,
                    (
                        tenant_id,
                        index_id,
                        item.id,
                        dimension,
                        json.dumps(item.vector),
                        json.dumps(item.metadata, ensure_ascii=False, sort_keys=True),
                    ),
                )
            self._conn.commit()
        return dimension

    def search(
        self,
        tenant_id: str,
        index_id: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, object],
    ) -> tuple[int, list[SearchHit]]:
        """Load candidate vectors from SQLite and rank them in process."""
        with self._lock:
            index_row = self._conn.execute(
                "SELECT dimension FROM indexes WHERE tenant_id = ? AND index_id = ?",
                (tenant_id, index_id),
            ).fetchone()
            if index_row is None:
                raise PlatformError(
                    code="VEC-NOTFOUND-404001",
                    message="index not found",
                    error_type="not_found_error",
                    status_code=404,
                )
            dimension = int(index_row["dimension"])
            if len(vector) != dimension:
                raise PlatformError(
                    code="VEC-VAL-400001",
                    message="query vector dimension does not match index dimension",
                    error_type="validation_error",
                    status_code=400,
                )

            rows = self._conn.execute(
                """
                SELECT item_id, vector_json, metadata_json
                FROM vectors
                WHERE tenant_id = ? AND index_id = ?
                """,
                (tenant_id, index_id),
            ).fetchall()

        hits: list[SearchHit] = []
        for row in rows:
            metadata = json.loads(str(row["metadata_json"]))
            if not matches_filters(metadata, filters):
                continue
            item_vector = json.loads(str(row["vector_json"]))
            score = round(cosine_similarity(vector, item_vector), 6)
            hits.append(SearchHit(id=str(row["item_id"]), score=score, metadata=metadata))

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return dimension, hits[:top_k]

    def _initialize(self) -> None:
        """Create SQLite tables for index metadata and vector payloads."""
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS indexes (
                    tenant_id TEXT NOT NULL,
                    index_id TEXT NOT NULL,
                    dimension INTEGER NOT NULL,
                    PRIMARY KEY (tenant_id, index_id)
                );
                CREATE TABLE IF NOT EXISTS vectors (
                    tenant_id TEXT NOT NULL,
                    index_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    dimension INTEGER NOT NULL,
                    vector_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_id, index_id, item_id)
                );
                """
            )
            self._conn.commit()

    @staticmethod
    def _connect(path: str) -> sqlite3.Connection:
        """Open a SQLite connection and create the parent directory if needed."""
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
