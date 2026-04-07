from __future__ import annotations

from typing import Any

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.internal.queue import (
    DeadLetterRecord,
    QueueBackendInfo,
    TaskQueue,
    TaskQueueMessage,
)


class RedisStreamTaskQueue(TaskQueue):
    """Task queue backed by Redis Streams and a consumer group.

    This backend implements at-least-once delivery:
    - enqueue: `XADD`
    - dequeue: `XREADGROUP`
    - ack: `XACK` + `XDEL`
    - dead-letter: separate Redis Stream
    """

    def __init__(
        self,
        *,
        url: str,
        stream_key: str,
        consumer_group: str,
        consumer_name: str,
        dead_letter_stream_key: str,
        block_milliseconds: int = 1000,
    ) -> None:
        self._url = url
        self._stream_key = stream_key
        self._consumer_group = consumer_group
        self._consumer_name = consumer_name
        self._dead_letter_stream_key = dead_letter_stream_key
        self._block_milliseconds = block_milliseconds
        self._driver: Any = None
        self._client: Any = None
        self._group_ready = False

    async def startup(self) -> None:
        """Initialize the Redis client and ensure the consumer group exists."""
        if self._client is None:
            self._driver = self._load_driver()
            self._client = self._create_client(self._driver)
        await self._ensure_consumer_group()

    async def shutdown(self) -> None:
        """Close the Redis client if the runtime provides an async close hook."""
        if self._client is None:
            return
        close = getattr(self._client, "aclose", None)
        if close is not None:
            await close()
        else:
            close = getattr(self._client, "close", None)
            if close is not None:
                maybe_result = close()
                if hasattr(maybe_result, "__await__"):
                    await maybe_result
        self._client = None
        self._group_ready = False

    def backend_info(self) -> QueueBackendInfo:
        return QueueBackendInfo(
            backend="redis_stream",
            delivery_semantics="at_least_once",
            queue_depth_mode="exact",
            dead_letter_count_mode="exact",
        )

    async def enqueue(self, message: TaskQueueMessage) -> None:
        """Append a new task message to the primary task stream."""
        client = await self._ensure_client()
        await client.xadd(
            self._stream_key,
            {
                "task_id": message.task_id,
                "request_id": message.request_id,
                "attempt": str(message.attempt),
            },
        )

    async def dequeue(self) -> TaskQueueMessage:
        """Block on the consumer group until the next task message is available."""
        client = await self._ensure_client()
        while True:
            result = await client.xreadgroup(
                groupname=self._consumer_group,
                consumername=self._consumer_name,
                streams={self._stream_key: ">"},
                count=1,
                block=self._block_milliseconds,
            )
            if not result:
                continue

            _stream_name, entries = result[0]
            if not entries:
                continue

            message_id, raw_fields = entries[0]
            fields = self._normalize_map(raw_fields)
            return TaskQueueMessage(
                task_id=str(fields["task_id"]),
                request_id=str(fields["request_id"]),
                attempt=int(fields.get("attempt", "1")),
                receipt_handle=str(message_id),
                backend_metadata={"stream_key": self._stream_key},
            )

    async def task_done(self, message: TaskQueueMessage) -> None:
        """Acknowledge and delete the processed stream entry."""
        if message.receipt_handle is None:
            return
        client = await self._ensure_client()
        stream_key = str(message.backend_metadata.get("stream_key", self._stream_key))
        await client.xack(stream_key, self._consumer_group, message.receipt_handle)
        await client.xdel(stream_key, message.receipt_handle)

    async def add_dead_letter(self, record: DeadLetterRecord) -> None:
        """Persist a terminal failure into the dedicated dead-letter stream."""
        client = await self._ensure_client()
        await client.xadd(
            self._dead_letter_stream_key,
            {
                "task_id": record.task_id,
                "request_id": record.request_id,
                "attempt": str(record.attempt),
                "error_code": record.error_code,
                "error_message": record.error_message,
            },
        )

    async def qsize(self) -> int:
        """Return the current live stream length after acknowledged deletions."""
        client = await self._ensure_client()
        return int(await client.xlen(self._stream_key))

    async def dead_letter_count(self) -> int:
        """Return the total number of dead-lettered messages retained in Redis."""
        client = await self._ensure_client()
        return int(await client.xlen(self._dead_letter_stream_key))

    async def _ensure_client(self) -> Any:
        if self._client is None:
            await self.startup()
        return self._client

    async def _ensure_consumer_group(self) -> None:
        if self._group_ready:
            return
        client = self._client
        if client is None:
            raise PlatformError(
                code="SYS-INTERNAL-500001",
                message="redis client is not initialized",
                error_type="internal_error",
                status_code=500,
            )
        try:
            await client.xgroup_create(
                name=self._stream_key,
                groupname=self._consumer_group,
                id="0",
                mkstream=True,
            )
        except Exception as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._group_ready = True

    def _create_client(self, driver: Any) -> Any:
        client_factory = getattr(driver, "from_url", None)
        if callable(client_factory):
            return client_factory(self._url, decode_responses=True)
        redis_cls = getattr(driver, "Redis", None)
        if redis_cls is not None and hasattr(redis_cls, "from_url"):
            return redis_cls.from_url(self._url, decode_responses=True)
        raise PlatformError(
            code="SYS-INTERNAL-500001",
            message="redis driver does not expose a supported client factory",
            error_type="internal_error",
            status_code=500,
        )

    @staticmethod
    def _normalize_map(raw_fields: Any) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        if isinstance(raw_fields, dict):
            for key, value in raw_fields.items():
                normalized[str(RedisStreamTaskQueue._normalize_scalar(key))] = RedisStreamTaskQueue._normalize_scalar(
                    value
                )
        return normalized

    @staticmethod
    def _normalize_scalar(value: Any) -> Any:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return value

    @staticmethod
    def _load_driver() -> Any:
        try:
            import redis.asyncio as redis  # type: ignore
        except ModuleNotFoundError as exc:
            raise PlatformError(
                code="SYS-INTERNAL-500001",
                message="redis is required for redis_stream queue support",
                error_type="internal_error",
                status_code=500,
            ) from exc
        return redis
