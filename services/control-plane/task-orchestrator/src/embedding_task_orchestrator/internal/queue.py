from __future__ import annotations

import asyncio
from dataclasses import dataclass
import os
import sqlite3
from threading import Lock
from time import time
from typing import Optional, Protocol


@dataclass(frozen=True)
class TaskQueueMessage:
    """Queued work item consumed by the task worker loop."""

    task_id: str
    request_id: str
    attempt: int = 1
    queue_id: Optional[int] = None


@dataclass(frozen=True)
class DeadLetterRecord:
    """Terminally failed queue item captured for later inspection or replay."""

    task_id: str
    request_id: str
    attempt: int
    error_code: str
    error_message: str


class TaskQueue(Protocol):
    """Queue abstraction used by the worker loop for task dispatch and dead-letter handling."""

    async def enqueue(self, message: TaskQueueMessage) -> None:
        """Enqueue a task for asynchronous processing."""
        ...

    async def dequeue(self) -> TaskQueueMessage:
        """Claim the next available task, blocking until work is available."""
        ...

    def task_done(self, message: TaskQueueMessage) -> None:
        """Acknowledge successful handling of a claimed queue message."""
        ...

    def add_dead_letter(self, record: DeadLetterRecord) -> None:
        """Persist a failed message into the dead-letter store."""
        ...

    def qsize(self) -> int:
        """Return the approximate count of pending queue messages."""
        ...

    def dead_letter_count(self) -> int:
        """Return the total count of dead-lettered messages."""
        ...


class InMemoryTaskQueue(TaskQueue):
    """Ephemeral queue implementation used by tests and local scaffold mode."""

    def __init__(self) -> None:
        self._queue: Optional[asyncio.Queue[TaskQueueMessage]] = None
        self._dead_letters: list[DeadLetterRecord] = []

    async def enqueue(self, message: TaskQueueMessage) -> None:
        queue = self._ensure_queue()
        await queue.put(message)

    async def dequeue(self) -> TaskQueueMessage:
        queue = self._ensure_queue()
        return await queue.get()

    def task_done(self, message: TaskQueueMessage) -> None:
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


class SqliteTaskQueue(TaskQueue):
    """Single-node durable queue backed by SQLite tables."""

    def __init__(self, *, path: str, poll_interval_seconds: float = 0.1) -> None:
        self._path = path
        self._poll_interval_seconds = poll_interval_seconds
        self._lock = Lock()
        self._conn = self._connect(path)
        self._initialize()

    async def enqueue(self, message: TaskQueueMessage) -> None:
        """Persist a new queue message that is ready for immediate delivery."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO task_queue (task_id, request_id, attempt, available_at)
                VALUES (?, ?, ?, ?)
                """,
                (message.task_id, message.request_id, message.attempt, time()),
            )
            self._conn.commit()

    async def dequeue(self) -> TaskQueueMessage:
        """Poll SQLite until one available row can be atomically claimed."""
        while True:
            message = self._claim_next()
            if message is not None:
                return message
            await asyncio.sleep(self._poll_interval_seconds)

    def task_done(self, message: TaskQueueMessage) -> None:
        """Delete the claimed row after the worker finishes processing it."""
        if message.queue_id is None:
            return
        with self._lock:
            self._conn.execute("DELETE FROM task_queue WHERE id = ?", (message.queue_id,))
            self._conn.commit()

    def add_dead_letter(self, record: DeadLetterRecord) -> None:
        """Append a terminal failure record for later operational inspection."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO dead_letters (task_id, request_id, attempt, error_code, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.task_id,
                    record.request_id,
                    record.attempt,
                    record.error_code,
                    record.error_message,
                    time(),
                ),
            )
            self._conn.commit()

    def qsize(self) -> int:
        """Count currently unclaimed queue rows."""
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM task_queue WHERE claimed_at IS NULL"
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def dead_letter_count(self) -> int:
        """Count rows stored in the dead-letter table."""
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM dead_letters").fetchone()
        return int(row[0]) if row is not None else 0

    def _claim_next(self) -> Optional[TaskQueueMessage]:
        """Claim the oldest available row and convert it to a queue message."""
        with self._lock:
            now = time()
            row = self._conn.execute(
                """
                SELECT id, task_id, request_id, attempt
                FROM task_queue
                WHERE claimed_at IS NULL AND available_at <= ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (now,),
            ).fetchone()
            if row is None:
                return None
            self._conn.execute(
                "UPDATE task_queue SET claimed_at = ? WHERE id = ? AND claimed_at IS NULL",
                (now, row["id"]),
            )
            self._conn.commit()
            return TaskQueueMessage(
                task_id=str(row["task_id"]),
                request_id=str(row["request_id"]),
                attempt=int(row["attempt"]),
                queue_id=int(row["id"]),
            )

    def _initialize(self) -> None:
        """Create queue and dead-letter tables when the database is first opened."""
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS task_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    available_at REAL NOT NULL,
                    claimed_at REAL
                );
                CREATE TABLE IF NOT EXISTS dead_letters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    error_code TEXT NOT NULL,
                    error_message TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )
            self._conn.commit()

    @staticmethod
    def _connect(path: str) -> sqlite3.Connection:
        """Open a SQLite connection and create the parent directory when needed."""
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
