from __future__ import annotations

import json
from typing import Any, Optional

from embedding_platform_common.errors import PlatformError
from embedding_task_orchestrator.internal.queue import (
    DeadLetterRecord,
    QueueBackendInfo,
    TaskQueue,
    TaskQueueMessage,
)


class KafkaTaskQueue(TaskQueue):
    """Task queue backed by Kafka topics and a consumer group.

    This backend keeps queue semantics aligned with the rest of the platform:
    - producer writes task messages to the main topic
    - consumer group claims records from that topic
    - worker commits offsets only after successful or terminal handling
    - dead-lettered tasks are forwarded to a dedicated DLQ topic
    """

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
        dead_letter_topic: str,
        group_id: str,
        client_id: str,
        poll_timeout_milliseconds: int = 1000,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topic = topic
        self._dead_letter_topic = dead_letter_topic
        self._group_id = group_id
        self._client_id = client_id
        self._poll_timeout_milliseconds = poll_timeout_milliseconds
        self._driver: Any = None
        self._producer: Any = None
        self._consumer: Any = None

    async def startup(self) -> None:
        """Create and start Kafka producer and consumer instances."""
        if self._producer is not None and self._consumer is not None:
            return
        self._driver = self._load_driver()
        self._producer = self._driver.AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            client_id=self._client_id,
        )
        self._consumer = self._driver.AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            client_id=self._client_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        await self._producer.start()
        await self._consumer.start()

    async def shutdown(self) -> None:
        """Stop Kafka clients and release socket resources."""
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    def backend_info(self) -> QueueBackendInfo:
        return QueueBackendInfo(
            backend="kafka",
            delivery_semantics="at_least_once",
            queue_depth_mode="approximate",
            dead_letter_count_mode="unsupported",
        )

    async def enqueue(self, message: TaskQueueMessage) -> None:
        """Publish a task message to the primary Kafka topic."""
        producer = await self._ensure_producer()
        payload = self._encode(
            {
                "task_id": message.task_id,
                "request_id": message.request_id,
                "attempt": message.attempt,
            }
        )
        await producer.send_and_wait(self._topic, value=payload)

    async def dequeue(self) -> TaskQueueMessage:
        """Poll Kafka until a record is available for the configured consumer group."""
        consumer = await self._ensure_consumer()
        while True:
            batches = await consumer.getmany(timeout_ms=self._poll_timeout_milliseconds, max_records=1)
            for topic_partition, records in batches.items():
                if not records:
                    continue
                record = records[0]
                payload = self._decode(record.value)
                return TaskQueueMessage(
                    task_id=str(payload["task_id"]),
                    request_id=str(payload["request_id"]),
                    attempt=int(payload.get("attempt", 1)),
                    receipt_handle=f"{record.topic}:{record.partition}:{record.offset}",
                    backend_metadata={
                        "topic": record.topic,
                        "partition": int(record.partition),
                        "offset": int(record.offset),
                    },
                )

    async def task_done(self, message: TaskQueueMessage) -> None:
        """Commit the consumed Kafka offset after the worker finishes handling it."""
        consumer = await self._ensure_consumer()
        topic = str(message.backend_metadata.get("topic", self._topic))
        partition = int(message.backend_metadata.get("partition", -1))
        offset = int(message.backend_metadata.get("offset", -1))
        if partition < 0 or offset < 0:
            return
        topic_partition = self._driver.TopicPartition(topic, partition)
        await consumer.commit({topic_partition: offset + 1})

    async def add_dead_letter(self, record: DeadLetterRecord) -> None:
        """Publish terminal failures to the configured Kafka dead-letter topic."""
        producer = await self._ensure_producer()
        payload = self._encode(
            {
                "task_id": record.task_id,
                "request_id": record.request_id,
                "attempt": record.attempt,
                "error_code": record.error_code,
                "error_message": record.error_message,
            }
        )
        await producer.send_and_wait(self._dead_letter_topic, value=payload)

    async def qsize(self) -> int:
        """Estimate backlog for the current consumer assignment using end offsets."""
        consumer = await self._ensure_consumer()
        assignment = consumer.assignment()
        if not assignment:
            return 0
        end_offsets = await consumer.end_offsets(list(assignment))
        backlog = 0
        for topic_partition in assignment:
            position = await consumer.position(topic_partition)
            backlog += max(int(end_offsets.get(topic_partition, 0)) - int(position), 0)
        return backlog

    async def dead_letter_count(self) -> int:
        """Kafka DLQ depth is not computed in-process in the MVP queue contract."""
        return 0

    async def _ensure_producer(self) -> Any:
        if self._producer is None:
            await self.startup()
        return self._producer

    async def _ensure_consumer(self) -> Any:
        if self._consumer is None:
            await self.startup()
        return self._consumer

    @staticmethod
    def _encode(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")

    @staticmethod
    def _decode(payload: Any) -> dict[str, Any]:
        if isinstance(payload, bytes):
            return json.loads(payload.decode("utf-8"))
        if isinstance(payload, str):
            return json.loads(payload)
        if isinstance(payload, dict):
            return payload
        raise PlatformError(
            code="SYS-INTERNAL-500001",
            message="unsupported kafka payload type",
            error_type="internal_error",
            status_code=500,
        )

    @staticmethod
    def _load_driver() -> Any:
        try:
            import aiokafka  # type: ignore
        except ModuleNotFoundError as exc:
            raise PlatformError(
                code="SYS-INTERNAL-500001",
                message="aiokafka is required for kafka queue support",
                error_type="internal_error",
                status_code=500,
            ) from exc
        return aiokafka
