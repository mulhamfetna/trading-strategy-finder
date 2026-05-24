"""Bridge between Optuna study events and an SSE event queue.

Reuses the producer/consumer pattern from `_box_event_stream` in src/api/app.py:
  1. A daemon worker thread runs `run_study()` and pushes events into a Queue.
  2. The HTTP request generator pops events and serialises them as SSE frames.
"""
from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Dict


_SENTINEL_DONE = object()


class StudyEventBridge:
    """Holds the queue + stop flag for one study run."""

    def __init__(self, maxsize: int = 512) -> None:
        self.q: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()

    def on_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Producer-side callback. Pushes onto the queue."""
        self.q.put((event_type, payload))

    def should_stop(self) -> bool:
        return self._stop.is_set()

    def request_stop(self) -> None:
        self._stop.set()

    def signal_done(self) -> None:
        """Producer marks the queue as drained."""
        self.q.put(_SENTINEL_DONE)

    def drain(self):
        """Consumer-side generator. Yields (event_type, payload) until SENTINEL."""
        while True:
            item = self.q.get()
            if item is _SENTINEL_DONE:
                return
            yield item


def make_worker(
    target: Callable[[], None],
    bridge: StudyEventBridge,
) -> threading.Thread:
    """Wrap `target` so it always signals done, even on exception."""
    def run():
        try:
            target()
        finally:
            bridge.signal_done()
    return threading.Thread(target=run, daemon=True)
