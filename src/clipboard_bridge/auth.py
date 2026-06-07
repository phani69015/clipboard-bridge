"""PIN validation and brute-force lockout tracking.

The PIN itself is loaded/persisted by `clipboard_bridge.config`. This
module holds the active PIN in memory (set via `set_pin()` at startup)
and tracks failed attempts per remote IP for rate-limiting.

Lockout: 5 failed attempts within a 60s rolling window per IP locks
that IP out for the remainder of the window.
"""

from __future__ import annotations

import hmac
import time
from threading import Lock

LOCKOUT_THRESHOLD = 5
LOCKOUT_WINDOW_SEC = 60

# Module-level state.
_pin: str | None = None
_attempts: dict[str, list[float]] = {}
_lock = Lock()


def set_pin(pin: str) -> None:
    """Set the active PIN. Called once at startup by the app factory."""
    global _pin
    if not isinstance(pin, str) or len(pin) != 4 or not pin.isdigit():
        raise ValueError("PIN must be a 4-digit string.")
    _pin = pin


def get_pin() -> str:
    if _pin is None:
        raise RuntimeError("PIN not set. Call set_pin() at startup.")
    return _pin


def validate_pin(supplied: str) -> bool:
    """Constant-time comparison against the active PIN."""
    if not isinstance(supplied, str):
        return False
    return hmac.compare_digest(supplied, get_pin())


def _prune(ip: str, now: float) -> None:
    cutoff = now - LOCKOUT_WINDOW_SEC
    if ip in _attempts:
        _attempts[ip] = [t for t in _attempts[ip] if t >= cutoff]
        if not _attempts[ip]:
            del _attempts[ip]


def is_locked_out(ip: str) -> bool:
    now = time.monotonic()
    with _lock:
        _prune(ip, now)
        return len(_attempts.get(ip, [])) >= LOCKOUT_THRESHOLD


def register_failure(ip: str) -> None:
    now = time.monotonic()
    with _lock:
        _prune(ip, now)
        _attempts.setdefault(ip, []).append(now)


def clear_attempts(ip: str) -> None:
    with _lock:
        _attempts.pop(ip, None)
