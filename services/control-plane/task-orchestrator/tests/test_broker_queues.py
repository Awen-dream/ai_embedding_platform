import asyncio
import json
import unittest

from embedding_task_orchestrator.internal.kafka_queue import KafkaTaskQueue
from embedding_task_orchestrator.internal.queue import DeadLetterRecord, TaskQueueMessage
from embedding_task_orchestrator.internal.redis_stream_queue import RedisStreamTaskQueue


class FakeRedisClient:
    def __init__(self) -> None:
        self.streams = {}
        self.groups = set()
        self.acks = []
        self.closed = False

    async def xgroup_create(self, name, groupname, id, mkstream):
        key = (name, groupname)
        if key in self.groups:
            raise RuntimeError("BUSYGROUP Consumer Group name already exists")
        self.groups.add(key)
        self.streams.setdefault(name, [])

    async def xadd(self, stream_key, fields):
        stream = self.streams.setdefault(stream_key, [])
        message_id = f"{len(stream) + 1}-0"
        stream.append((message_id, dict(fields)))
        return message_id

    async def xreadgroup(self, groupname, consumername, streams, count, block):
        del groupname, consumername, count, block
        stream_key = list(streams.keys())[0]
        entries = self.streams.get(stream_key, [])
        if not entries:
            return []
        return [(stream_key, [entries[0]])]

    async def xack(self, stream_key, group_name, receipt_handle):
        self.acks.append((stream_key, group_name, receipt_handle))

    async def xdel(self, stream_key, receipt_handle):
        entries = self.streams.get(stream_key, [])
        self.streams[stream_key] = [entry for entry in entries if entry[0] != receipt_handle]

    async def xlen(self, stream_key):
        return len(self.streams.get(stream_key, []))

    async def aclose(self):
        self.closed = True


class FakeRedisDriver:
    def __init__(self) -> None:
        self.client = FakeRedisClient()

    def from_url(self, url, decode_responses=True):
        del url, decode_responses
        return self.client


class FakeTopicPartition:
    def __init__(self, topic, partition):
        self.topic = topic
        self.partition = partition

    def __hash__(self):
        return hash((self.topic, self.partition))

    def __eq__(self, other):
        return isinstance(other, FakeTopicPartition) and (self.topic, self.partition) == (
            other.topic,
            other.partition,
        )


class FakeRecord:
    def __init__(self, topic, partition, offset, value):
        self.topic = topic
        self.partition = partition
        self.offset = offset
        self.value = value


class FakeProducer:
    def __init__(self) -> None:
        self.sent = []
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    async def send_and_wait(self, topic, value):
        self.sent.append((topic, value))


class FakeConsumer:
    def __init__(self) -> None:
        self.records = []
        self.started = False
        self.stopped = False
        self.commits = []
        self._assignment = set()
        self._positions = {}
        self._end_offsets = {}

    async def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    async def getmany(self, timeout_ms, max_records):
        del timeout_ms, max_records
        if not self.records:
            return {}
        record = self.records.pop(0)
        topic_partition = FakeTopicPartition(record.topic, record.partition)
        self._assignment = {topic_partition}
        self._positions[topic_partition] = record.offset + 1
        self._end_offsets[topic_partition] = record.offset + 1
        return {topic_partition: [record]}

    def assignment(self):
        return set(self._assignment)

    async def end_offsets(self, partitions):
        return {topic_partition: self._end_offsets.get(topic_partition, 0) for topic_partition in partitions}

    async def position(self, topic_partition):
        return self._positions.get(topic_partition, 0)

    async def commit(self, offsets):
        self.commits.append(offsets)


class FakeKafkaDriver:
    TopicPartition = FakeTopicPartition

    def __init__(self) -> None:
        self.producer = FakeProducer()
        self.consumer = FakeConsumer()

    def AIOKafkaProducer(self, **kwargs):
        del kwargs
        return self.producer

    def AIOKafkaConsumer(self, *topics, **kwargs):
        del topics, kwargs
        return self.consumer


class RedisStreamTaskQueueTest(unittest.TestCase):
    def test_redis_stream_queue_claims_acknowledges_and_dead_letters_messages(self) -> None:
        queue = RedisStreamTaskQueue(
            url="redis://127.0.0.1:6379/0",
            stream_key="embedding:tasks",
            consumer_group="embedding-task-workers",
            consumer_name="worker-1",
            dead_letter_stream_key="embedding:tasks:dlq",
            block_milliseconds=1,
        )
        driver = FakeRedisDriver()
        queue._load_driver = lambda: driver  # type: ignore[method-assign]

        asyncio.run(queue.startup())
        asyncio.run(queue.enqueue(TaskQueueMessage(task_id="task-1", request_id="req-1", attempt=2)))
        claimed = asyncio.run(queue.dequeue())

        self.assertEqual(claimed.task_id, "task-1")
        self.assertEqual(claimed.receipt_handle, "1-0")
        self.assertEqual(queue.backend_info().backend, "redis_stream")
        self.assertEqual(asyncio.run(queue.qsize()), 1)

        asyncio.run(queue.task_done(claimed))
        self.assertEqual(asyncio.run(queue.qsize()), 0)

        asyncio.run(
            queue.add_dead_letter(
                DeadLetterRecord(
                    task_id="task-1",
                    request_id="req-1",
                    attempt=2,
                    error_code="TASK-FAILED",
                    error_message="boom",
                )
            )
        )
        self.assertEqual(asyncio.run(queue.dead_letter_count()), 1)
        asyncio.run(queue.shutdown())
        self.assertTrue(driver.client.closed)


class KafkaTaskQueueTest(unittest.TestCase):
    def test_kafka_queue_publishes_consumes_and_commits_offsets(self) -> None:
        queue = KafkaTaskQueue(
            bootstrap_servers="127.0.0.1:9092",
            topic="embedding.tasks",
            dead_letter_topic="embedding.tasks.dlq",
            group_id="embedding-task-workers",
            client_id="task-orchestrator",
            poll_timeout_milliseconds=1,
        )
        driver = FakeKafkaDriver()
        driver.consumer.records.append(
            FakeRecord(
                topic="embedding.tasks",
                partition=0,
                offset=7,
                value=json.dumps(
                    {"task_id": "task-1", "request_id": "req-1", "attempt": 3}
                ).encode("utf-8"),
            )
        )
        queue._load_driver = lambda: driver  # type: ignore[method-assign]

        asyncio.run(queue.startup())
        asyncio.run(queue.enqueue(TaskQueueMessage(task_id="task-2", request_id="req-2", attempt=1)))
        claimed = asyncio.run(queue.dequeue())

        self.assertEqual(claimed.task_id, "task-1")
        self.assertEqual(claimed.backend_metadata["partition"], 0)
        self.assertEqual(queue.backend_info().queue_depth_mode, "approximate")
        self.assertEqual(asyncio.run(queue.qsize()), 0)

        asyncio.run(queue.task_done(claimed))
        self.assertEqual(len(driver.consumer.commits), 1)

        asyncio.run(
            queue.add_dead_letter(
                DeadLetterRecord(
                    task_id="task-1",
                    request_id="req-1",
                    attempt=3,
                    error_code="TASK-FAILED",
                    error_message="boom",
                )
            )
        )
        self.assertEqual(driver.producer.sent[0][0], "embedding.tasks")
        self.assertEqual(driver.producer.sent[1][0], "embedding.tasks.dlq")
        self.assertEqual(asyncio.run(queue.dead_letter_count()), 0)
        asyncio.run(queue.shutdown())
        self.assertTrue(driver.producer.stopped)
        self.assertTrue(driver.consumer.stopped)
