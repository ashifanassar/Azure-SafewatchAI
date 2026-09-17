from collections.abc import Callable
from time import sleep
from typing import TypeVar

T = TypeVar("T")


class RetryPolicy:
    def __init__(self, attempts: int = 3, delay_seconds: float = 0.1) -> None:
        if attempts < 1:
            raise ValueError("attempts must be at least 1")
        self.attempts = attempts
        self.delay_seconds = delay_seconds

    def run(self, fn: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                return fn()
            except Exception as exc:
                last_error = exc
                if attempt < self.attempts:
                    sleep(self.delay_seconds)
        if last_error is not None:
            raise last_error
        raise RuntimeError("retry policy exited without result")
