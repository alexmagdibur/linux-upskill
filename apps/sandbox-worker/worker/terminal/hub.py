"""TerminalHub: один долгоживущий PTY на сессию, к нему можно переподключаться.

Блокирующее чтение сокета идёт в отдельном потоке; в asyncio вывод передаётся через
ограниченную очередь (backpressure: если клиент не успевает, поток чтения блокируется,
а значит и процесс в контейнере замедляется, а не копит память).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
from collections import deque
from dataclasses import dataclass, field

from worker.runtime.base import PTYStream, RuntimeAdapter

log = logging.getLogger("worker.terminal")

QUEUE_CHUNKS = 64
SLOW_CONSUMER_TIMEOUT = 10.0


@dataclass
class Subscriber:
    queue: asyncio.Queue[bytes | None] = field(default_factory=lambda: asyncio.Queue(QUEUE_CHUNKS))
    closed: bool = False


class PtySession:
    def __init__(self, runtime_ref: str, pty: PTYStream, loop: asyncio.AbstractEventLoop, scrollback: int,
                 max_output: int) -> None:
        self.runtime_ref = runtime_ref
        self.pty = pty
        self._loop = loop
        self._max_output = max_output
        self._scrollback: deque[bytes] = deque()
        self._scrollback_size = 0
        self._scrollback_limit = scrollback
        self._lock = threading.Lock()
        self.subscriber: Subscriber | None = None
        self.total_output = 0
        self.exited = False
        self.output_limit_hit = False
        self._thread = threading.Thread(target=self._reader, name=f"pty-{runtime_ref[-8:]}", daemon=True)
        self._thread.start()

    # --- поток чтения -------------------------------------------------------
    def _reader(self) -> None:
        while True:
            data = self.pty.read_blocking()
            if not data:
                break
            self.total_output += len(data)
            if self.total_output > self._max_output:
                self.output_limit_hit = True
                break
            with self._lock:
                self._scrollback.append(data)
                self._scrollback_size += len(data)
                while self._scrollback_size > self._scrollback_limit and len(self._scrollback) > 1:
                    self._scrollback_size -= len(self._scrollback.popleft())
                sub = self.subscriber
            if sub and not sub.closed:
                fut = asyncio.run_coroutine_threadsafe(self._offer(sub, data), self._loop)
                try:
                    fut.result(timeout=SLOW_CONSUMER_TIMEOUT + 1)
                except Exception:  # noqa: BLE001
                    sub.closed = True
        self.exited = True
        sub = self.subscriber
        if sub:
            with contextlib.suppress(Exception):
                asyncio.run_coroutine_threadsafe(sub.queue.put(None), self._loop).result(timeout=2)

    @staticmethod
    async def _offer(sub: Subscriber, data: bytes) -> None:
        try:
            await asyncio.wait_for(sub.queue.put(data), SLOW_CONSUMER_TIMEOUT)
        except TimeoutError:
            sub.closed = True  # медленный потребитель: отключаем подписчика, PTY остаётся жив

    # --- API ----------------------------------------------------------------
    def attach(self) -> tuple[Subscriber, bytes]:
        """Подписаться на вывод; предыдущий подписчик (старая вкладка) отключается."""
        with self._lock:
            old = self.subscriber
            sub = Subscriber()
            replay = b"".join(self._scrollback)
            self.subscriber = sub
        if old:
            old.closed = True
            with contextlib.suppress(asyncio.QueueFull):
                old.queue.put_nowait(None)
        return sub, replay

    def detach(self, sub: Subscriber) -> None:
        with self._lock:
            if self.subscriber is sub:
                self.subscriber = None
        sub.closed = True

    async def write(self, data: bytes) -> None:
        await asyncio.to_thread(self.pty.write_blocking, data)

    async def resize(self, cols: int, rows: int) -> None:
        await asyncio.to_thread(self.pty.resize_blocking, cols, rows)

    def close(self) -> None:
        self.pty.close()


class TerminalHub:
    def __init__(self, adapter: RuntimeAdapter, scrollback: int, max_output: int) -> None:
        self._adapter = adapter
        self._sessions: dict[str, PtySession] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._scrollback = scrollback
        self._max_output = max_output

    async def get(self, runtime_ref: str) -> PtySession:
        lock = self._locks.setdefault(runtime_ref, asyncio.Lock())
        async with lock:
            sess = self._sessions.get(runtime_ref)
            if sess and not sess.exited:
                return sess
            if sess:
                sess.close()
            pty = await self._adapter.attach_terminal(runtime_ref)
            sess = PtySession(runtime_ref, pty, asyncio.get_running_loop(), self._scrollback, self._max_output)
            self._sessions[runtime_ref] = sess
            return sess

    def drop(self, runtime_ref: str) -> None:
        sess = self._sessions.pop(runtime_ref, None)
        self._locks.pop(runtime_ref, None)
        if sess:
            sess.close()
