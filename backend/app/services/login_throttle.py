from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
import time


@dataclass
class LoginAttemptLimiter:
    max_attempts: int
    window_seconds: int
    _attempts: dict[str, deque[float]] = field(default_factory=lambda: defaultdict(deque))
    _lock: Lock = field(default_factory=Lock)

    def _prune(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts[key]
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        if not attempts:
            self._attempts.pop(key, None)
            return deque()
        return attempts

    def retry_after(self, key: str, *, now: float | None = None) -> int | None:
        current_time = time.monotonic() if now is None else now
        with self._lock:
            attempts = self._prune(key, current_time)
            if len(attempts) < self.max_attempts:
                return None
            return max(1, int(self.window_seconds - (current_time - attempts[0])))

    def record_failure(self, key: str, *, now: float | None = None) -> None:
        current_time = time.monotonic() if now is None else now
        with self._lock:
            attempts = self._prune(key, current_time)
            if key not in self._attempts:
                self._attempts[key] = attempts
            attempts.append(current_time)

    def clear(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
