"""``perf_counter`` helpers for honest latency telemetry."""
from __future__ import annotations

import time
from types import TracebackType
from typing import Optional


class Timer:
    """Context manager measuring wall-clock milliseconds.

    >>> with Timer() as t:
    ...     pass
    >>> t.ms >= 0
    True
    """

    def __init__(self) -> None:
        self._start = 0.0
        self.ms = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.ms = (time.perf_counter() - self._start) * 1000.0

    def elapsed_ms(self) -> float:
        """Milliseconds since entering (valid while still inside the ``with`` block)."""
        return (time.perf_counter() - self._start) * 1000.0

