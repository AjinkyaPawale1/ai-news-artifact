"""Small retry helpers for transient external-service failures."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def retry_with_exponential_backoff(
    operation: Callable[[], T],
    *,
    max_retries: int,
    retry_on: Callable[[Exception], bool],
    on_retry: Callable[[Exception, int, float], None] | None = None,
    initial_delay: float = 1.0,
    max_delay: float = 8.0,
) -> T:
    """Run an operation with bounded exponential backoff and jitter."""
    retries = 0
    while True:
        try:
            return operation()
        except Exception as exc:
            if retries >= max_retries or not retry_on(exc):
                raise
            delay = min(max_delay, initial_delay * (2**retries))
            delay += random.uniform(0, delay * 0.25)
            retries += 1
            if on_retry:
                on_retry(exc, retries, delay)
            time.sleep(delay)
