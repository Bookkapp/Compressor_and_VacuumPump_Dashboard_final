from __future__ import annotations

import threading
import time
from typing import Any


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    def invalidate(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._store.pop(key, None)

    def invalidate_all(self) -> None:
        with self._lock:
            self._store.clear()


cache = TTLCache()
