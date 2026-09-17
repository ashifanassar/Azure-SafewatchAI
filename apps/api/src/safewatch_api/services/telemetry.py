from contextlib import contextmanager
from time import perf_counter
from typing import Iterator


class Telemetry:
    @contextmanager
    def trace(self, name: str, **properties: object) -> Iterator[None]:
        start = perf_counter()
        try:
            yield
        finally:
            duration_ms = round((perf_counter() - start) * 1000, 2)
            print({"trace": name, "duration_ms": duration_ms, **properties})

