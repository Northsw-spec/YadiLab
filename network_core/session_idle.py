"""Real-time, server-owned expiry for bounded in-memory session registries."""
from __future__ import annotations

from functools import wraps
from time import monotonic


IDLE_TIMEOUT_SECONDS = 60 * 60
CLEANUP_INTERVAL_SECONDS = 60
CLEANUP_JOIN_SECONDS = 5


class IdleSessions:
    """Methods are called under the registry's existing RLock."""

    def _init_idle(self, clock=None):
        self._idle_clock = monotonic if clock is None else clock
        self._last_activity: dict[str, float] = {}

    def _track(self, session_id: str) -> None:
        self._last_activity[session_id] = self._idle_clock()

    def _forget(self, session_id: str) -> None:
        self._last_activity.pop(session_id, None)

    def _reap_expired(self) -> int:
        now = self._idle_clock()
        expired = [sid for sid, last in self._last_activity.items()
                   if now - last >= IDLE_TIMEOUT_SECONDS]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._forget(sid)
        return len(expired)

    def cleanup_expired(self) -> int:
        with self._lock:
            return self._reap_expired()

    def _live(self, session_id: object) -> bool:
        if not isinstance(session_id, str) or session_id not in self._sessions:
            return False
        if self._idle_clock() - self._last_activity[session_id] >= IDLE_TIMEOUT_SECONDS:
            self._sessions.pop(session_id)
            self._forget(session_id)
            return False
        return True


def session_activity(operation):
    """Refresh only after a successful operation, before releasing its lock."""
    @wraps(operation)
    def wrapper(self, session_id, *args, **kwargs):
        with self._lock:
            result = operation(self, session_id, *args, **kwargs)
            self._track(session_id)
            return result
    return wrapper
