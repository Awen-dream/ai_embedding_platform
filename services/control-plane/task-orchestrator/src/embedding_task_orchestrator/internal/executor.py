from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Optional

import httpx

from embedding_platform_common.errors import PlatformError
from embedding_platform_common.ids import generate_id
from embedding_platform_common.observability import log_event
from embedding_task_orchestrator.internal.store import TaskStore
from embedding_task_orchestrator.models import TaskRecord


@dataclass(frozen=True)
class InlineTaskItem:
    item_id: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class InlineTaskSource:
    index_id: str
    dimension: Optional[int]
    preprocess: dict[str, Any]
    items: list[InlineTaskItem]


@dataclass(frozen=True)
class PreprocessedChunk:
    chunk_id: str
    item_id: str
    text: str
    metadata: dict[str, Any]
    start_word: int
    end_word: int


def normalize_inline_source(source: dict[str, Any], default_index_id: str) -> InlineTaskSource:
    source_type = source.get("type")
    if source_type != "inline":
        raise PlatformError(
            code="TASK-VAL-400001",
            message="only source.type=inline is supported in the MVP",
            error_type="validation_error",
            status_code=400,
            details={"source_type": source_type},
        )

    raw_items = source.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise PlatformError(
            code="TASK-VAL-400001",
            message="source.items must be a non-empty list",
            error_type="validation_error",
            status_code=400,
        )

    items: list[InlineTaskItem] = []
    for index, raw_item in enumerate(raw_items):
        if isinstance(raw_item, str):
            text = raw_item.strip()
            metadata: dict[str, Any] = {}
            item_id = generate_id("doc")
        elif isinstance(raw_item, dict):
            text = str(raw_item.get("text", "")).strip()
            metadata = dict(raw_item.get("metadata", {}))
            item_id = str(raw_item.get("id") or generate_id("doc"))
        else:
            raise PlatformError(
                code="TASK-VAL-400001",
                message="source.items entries must be string or object",
                error_type="validation_error",
                status_code=400,
                details={"item_index": index},
            )

        if not text:
            raise PlatformError(
                code="TASK-VAL-400001",
                message="inline source item text must not be empty",
                error_type="validation_error",
                status_code=400,
                details={"item_index": index},
            )

        items.append(InlineTaskItem(item_id=item_id, text=text, metadata=metadata))

    dimension = source.get("dimension")
    if dimension is not None and (not isinstance(dimension, int) or dimension <= 0):
        raise PlatformError(
            code="TASK-VAL-400001",
            message="source.dimension must be a positive integer",
            error_type="validation_error",
            status_code=400,
        )

    index_id = str(source.get("index_id") or default_index_id)
    preprocess = dict(source.get("preprocess", {}))
    return InlineTaskSource(index_id=index_id, dimension=dimension, preprocess=preprocess, items=items)


async def execute_embedding_task(
    *,
    request_id: str,
    task: TaskRecord,
    store: TaskStore,
    settings: Any,
    logger: Any,
) -> None:
    source = normalize_inline_source(task.source, settings.default_index_id)

    store.transition(task.task_id, "preprocessing", progress=0.2)
    chunks, duplicate_count = await _preprocess_items(
        request_id=request_id,
        settings=settings,
        task=task,
        source=source,
    )
    log_event(
        logger,
        "embedding.preprocess.completed",
        request_id=request_id,
        task_id=task.task_id,
        input_count=len(source.items),
        chunk_count=len(chunks),
        duplicate_count=duplicate_count,
    )

    store.transition(task.task_id, "embedding", progress=0.55)
    embeddings = await _generate_embeddings(
        request_id=request_id,
        settings=settings,
        task=task,
        chunks=chunks,
        dimension=source.dimension,
    )
    log_event(
        logger,
        "embedding.runtime.completed",
        request_id=request_id,
        task_id=task.task_id,
        batch_size=len(chunks),
        model=task.model,
        vector_dimension=len(embeddings[0]) if embeddings else 0,
    )

    store.transition(task.task_id, "persisting", progress=0.85)
    upsert_count = await _upsert_embeddings(
        request_id=request_id,
        settings=settings,
        task=task,
        chunks=chunks,
        embeddings=embeddings,
    )
    log_event(
        logger,
        "embedding.vector.upserted",
        request_id=request_id,
        task_id=task.task_id,
        index_id=source.index_id,
        upsert_count=upsert_count,
    )

    store.transition(task.task_id, "succeeded", progress=1.0, error_code=None, error_message=None)
    log_event(
        logger,
        "embedding.task.succeeded",
        request_id=request_id,
        task_id=task.task_id,
        total_items=len(source.items),
        total_chunks=len(chunks),
        index_id=source.index_id,
    )


async def _generate_embeddings(
    *,
    request_id: str,
    settings: Any,
    task: TaskRecord,
    chunks: list[PreprocessedChunk],
    dimension: Optional[int],
) -> list[list[float]]:
    payload = {
        "tenant_id": task.tenant_id,
        "model": task.model,
        "modality": "text",
        "input": [chunk.text for chunk in chunks],
        "dimension": dimension,
        "metadata": {"task_id": task.task_id},
    }
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        data = await _post_json(
            client=client,
            url=f"{settings.runtime_url}/internal/embeddings",
            payload=payload,
            request_id=request_id,
        )
    return [row["embedding"] for row in data["data"]]


async def _upsert_embeddings(
    *,
    request_id: str,
    settings: Any,
    task: TaskRecord,
    chunks: list[PreprocessedChunk],
    embeddings: list[list[float]],
) -> int:
    items = []
    for chunk, embedding in zip(chunks, embeddings):
        metadata = {
            **chunk.metadata,
            "task_id": task.task_id,
            "tenant_id": task.tenant_id,
            "model": task.model,
            "text": chunk.text,
            "item_id": chunk.item_id,
            "chunk_id": chunk.chunk_id,
            "start_word": chunk.start_word,
            "end_word": chunk.end_word,
        }
        items.append({"id": chunk.chunk_id, "vector": embedding, "metadata": metadata})

    payload = {
        "tenant_id": task.tenant_id,
        "index_id": task.source.get("index_id") or settings.default_index_id,
        "items": items,
    }
    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        data = await _post_json(
            client=client,
            url=f"{settings.vector_store_url}/internal/vectors/upsert",
            payload=payload,
            request_id=request_id,
        )
    return int(data["upserted_count"])


async def _preprocess_items(
    *,
    request_id: str,
    settings: Any,
    task: TaskRecord,
    source: InlineTaskSource,
) -> tuple[list[PreprocessedChunk], int]:
    payload = {
        "tenant_id": task.tenant_id,
        "items": [
            {"id": item.item_id, "text": item.text, "metadata": item.metadata}
            for item in source.items
        ],
    }
    if "chunk_size_words" in source.preprocess:
        payload["chunk_size_words"] = source.preprocess["chunk_size_words"]
    if "overlap_words" in source.preprocess:
        payload["overlap_words"] = source.preprocess["overlap_words"]

    async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as client:
        data = await _post_json(
            client=client,
            url=f"{settings.preprocess_url}/internal/preprocess/text",
            payload=payload,
            request_id=request_id,
        )
    chunks = [
        PreprocessedChunk(
            chunk_id=raw_chunk["chunk_id"],
            item_id=raw_chunk["item_id"],
            text=raw_chunk["text"],
            metadata=raw_chunk.get("metadata", {}),
            start_word=raw_chunk["start_word"],
            end_word=raw_chunk["end_word"],
        )
        for raw_chunk in data["chunks"]
    ]
    return chunks, int(data.get("duplicate_count", 0))


async def _post_json(
    *,
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    try:
        response = await client.post(
            url,
            json=payload,
            headers={"x-request-id": request_id},
        )
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

    return _parse_response(response)


def _parse_response(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise PlatformError(
            code="SYS-DEP-502001",
            message="downstream response is not valid json",
            error_type="dependency_error",
            status_code=502,
            retryable=True,
        ) from exc

    if response.status_code >= 400:
        error = data.get("error", {})
        raise PlatformError(
            code=error.get("code", "SYS-DEP-502001"),
            message=error.get("message", "downstream service error"),
            error_type=error.get("type", "dependency_error"),
            status_code=response.status_code,
            retryable=error.get("retryable", response.status_code >= 500),
            details=error.get("details", {}),
        )
    return data
