"""Autotyper engine.

Holds a single text buffer and types it out character-by-character into
whatever app currently has keyboard focus when triggered. Runs in a
background daemon thread so the HTTP server stays responsive.

The buffer persists after typing completes, so the same queued text can
be re-typed by pressing the hotkey again. The only ways to drop the
buffer are: queue new text from the phone, hit "Clear queue", or
restart the server.

A second hotkey press while typing is in progress is ignored — the
in-flight type must finish (or be aborted via Esc) first.

The typing engine uses pynput's keyboard.Controller, which on macOS
synthesizes events through the Quartz Event Services API. This requires
Accessibility permission (granted to the terminal app running Python).
"""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import Literal

logger = logging.getLogger(__name__)

# Speed presets in seconds per character.
_SPEEDS = {
    "slow": 0.080,
    "normal": 0.030,
    "fast": 0.005,
}

MAX_CHARS = 10_000
START_DELAY_SEC = 2.0  # Pause after typing is triggered, so the user has
                       # time to focus the target window/field.

Status = Literal["idle", "queued", "typing"]

# ---------------------------------------------------------------------------
# Module-level state, lock-protected
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_buffer: str = ""
_speed: str = "normal"
_jitter: bool = False
_status: Status = "idle"
_progress: int = 0
_total: int = 0
_abort_flag = threading.Event()
_thread: threading.Thread | None = None


class AutotypeError(RuntimeError):
    """Raised for queue-time errors (validation, conflict)."""


def _set_status(new_status: Status) -> None:
    global _status
    _status = new_status


def queue(text: str, speed: str = "normal", jitter: bool = False) -> None:
    """Store text to be typed when the hotkey fires."""
    if not isinstance(text, str) or not text:
        raise AutotypeError("Text is required.")
    if len(text) > MAX_CHARS:
        raise AutotypeError(f"Text too long (max {MAX_CHARS} characters).")
    if speed not in _SPEEDS:
        raise AutotypeError(f"Invalid speed. Use one of: {', '.join(_SPEEDS)}")

    global _buffer, _speed, _jitter, _progress, _total
    with _lock:
        if _status == "typing":
            raise AutotypeError("Currently typing. Press Esc to abort first.")
        _buffer = text
        _speed = speed
        _jitter = bool(jitter)
        _progress = 0
        _total = len(text)
        _abort_flag.clear()
        _set_status("queued")


def clear() -> None:
    global _buffer, _progress, _total
    with _lock:
        if _status == "typing":
            # Don't blow away mid-typing state; user should abort first.
            return
        _buffer = ""
        _progress = 0
        _total = 0
        _set_status("idle")


def abort() -> None:
    """Signal the typing thread to stop at the next character boundary."""
    if _status == "typing":
        _abort_flag.set()


def status() -> dict:
    with _lock:
        preview = _buffer[:80] + ("..." if len(_buffer) > 80 else "")
        return {
            "status": _status,
            "progress": _progress,
            "total": _total,
            "speed": _speed,
            "jitter": _jitter,
            "preview": preview,
        }


def start_typing() -> bool:
    """Spawn the typing thread if a buffer is queued. Returns True on start."""
    global _thread
    with _lock:
        if _status != "queued":
            logger.info("start_typing called but status=%s; no-op", _status)
            return False
        _set_status("typing")
        _abort_flag.clear()
        _thread = threading.Thread(target=_type_loop, name="autotyper", daemon=True)
        _thread.start()
        return True


def _delay() -> float:
    base = _SPEEDS[_speed]
    if _jitter:
        # +/- 20% jitter, clamped to a positive value.
        factor = 1.0 + random.uniform(-0.2, 0.2)
        return max(0.001, base * factor)
    return base


def _type_loop() -> None:
    global _progress

    # Lazy import: server should still boot if pynput is missing or denied.
    try:
        from pynput.keyboard import Controller
    except Exception as exc:  # pragma: no cover
        logger.error("pynput not available: %s", exc)
        with _lock:
            # Buffer is intact; re-arm so the user can retry once they fix
            # the environment.
            _set_status("queued" if _buffer else "idle")
            _progress = 0
        return

    controller = Controller()

    # Snapshot buffer under lock so subsequent edits don't affect this run.
    with _lock:
        text = _buffer

    # Pre-typing delay to let the user focus the target window.
    deadline = time.monotonic() + START_DELAY_SEC
    while time.monotonic() < deadline:
        if _abort_flag.is_set():
            with _lock:
                # Aborted before typing started — buffer remains queued.
                _set_status("queued")
                _progress = 0
                _abort_flag.clear()
            return
        time.sleep(0.05)

    try:
        for i, ch in enumerate(text, start=1):
            if _abort_flag.is_set():
                with _lock:
                    _set_status("queued")
                    _progress = 0
                    _abort_flag.clear()
                return
            try:
                controller.type(ch)
            except Exception as exc:  # pragma: no cover
                # Some characters can fail on certain layouts; log and continue.
                logger.warning("Failed to type char %r: %s", ch, exc)
            with _lock:
                _progress = i
            time.sleep(_delay())
    finally:
        with _lock:
            # Re-arm: buffer is preserved so the hotkey can fire again.
            if _status == "typing":
                _set_status("queued")
                _progress = 0
                _abort_flag.clear()
