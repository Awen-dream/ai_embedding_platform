from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TaskQueueMessage:
    task_id: str
    request_id: str
    attempt: int = 1


@dataclass(frozen=True)
class DeadLetterRecord:
    task_id: str
    request_id: str
    attempt: int
    error_code: str
    error_message: str


class InMemoryTaskQueue:
    def __init__(self) -> None:
        self._queue: Optional[asyncio.Queue[TaskQueueMessage]] = None
        self._dead_letters: list[DeadLetterRecord] = []

    async def enqueue(self, message: TaskQueueMessage) -> None:
        queue = self._ensure_queue()
        await queue.put(message)

    async def dequeue(self) -> TaskQueueMessage:
        queue = self._ensure_queue()
        return await queue.get()

    def task_done(self) -> None:
        if self._queue is not None:
            self._queue.task_done()

    def add_dead_letter(self, record: DeadLetterRecord) -> None:
        self._dead_letters.append(record)

    def qsize(self) -> int:
        if self._queue is None:
            return 0
        return self._queue.qsize()

    def dead_letter_count(self) -> int:
        return len(self._dead_letters)

    def _ensure_queue(self) -> asyncio.Queue[TaskQueueMessage]:
        if self._queue is None:
            self._queue = asyncio.Queue()
        return self._queue
