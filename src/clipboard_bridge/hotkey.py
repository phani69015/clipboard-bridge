"""Global hotkey listener for the autotyper.

Two bindings:
- type hotkey   -> autotype.start_typing()
- abort hotkey  -> autotype.abort()

On macOS, both listening to and synthesizing key events require
Accessibility permission for the terminal app running this script
(System Settings -> Privacy & Security -> Accessibility).

The diagnostic Listener (started alongside the hotkey listener) prints
a message the first time it sees any key event, so you can tell at a
glance whether Accessibility permission is actually granted: if you
press a key and nothing prints, the permission is missing.
"""

from __future__ import annotations

import logging
import threading
import time

from . import autotype

logger = logging.getLogger(__name__)

_listener = None
_diag_listener = None
_started = False
_lock = threading.Lock()
_first_key_seen = False
_started_at: float | None = None


def _make_handler_type():
    def _handler():
        print("[hotkey] type hotkey pressed", flush=True)
        try:
            started = autotype.start_typing()
            if not started:
                print(
                    "[hotkey] nothing to do "
                    "(buffer empty, or already typing). "
                    "Queue something from the phone first.",
                    flush=True,
                )
        except Exception as exc:  # pragma: no cover
            logger.exception("Type hotkey handler failed: %s", exc)
    return _handler


def _make_handler_abort():
    def _handler():
        try:
            autotype.abort()
        except Exception as exc:  # pragma: no cover
            logger.exception("Abort hotkey handler failed: %s", exc)
    return _handler


def _diagnostic_on_press(_key):
    """Fires for any key press. Used to confirm Accessibility works."""
    global _first_key_seen
    if not _first_key_seen:
        _first_key_seen = True
        print(
            "[hotkey] OK - first key event received. "
            "Accessibility permission is working.",
            flush=True,
        )


def _accessibility_warning_thread() -> None:
    """If no key events are seen within 10 seconds of starting, warn the
    user that Accessibility permission probably isn't granted."""
    time.sleep(10.0)
    if not _first_key_seen:
        print(
            "\n[hotkey] WARNING: no key events received in 10 seconds.\n"
            "         This almost always means Accessibility permission "
            "is not granted.\n"
            "         Open: System Settings > Privacy & Security > "
            "Accessibility\n"
            "         Enable your terminal app (e.g. Terminal, iTerm, "
            "Visual Studio Code).\n"
            "         Then quit the terminal app entirely (Cmd+Q on the "
            "app, not just\n"
            "         the window) and rerun: python server.py\n",
            flush=True,
        )


def start_hotkey_listener(
    type_hotkey: str = "<ctrl>+a",
    abort_hotkey: str = "<esc>",
) -> bool:
    """Start the listener in a background thread. Idempotent."""
    global _listener, _diag_listener, _started, _started_at, _first_key_seen
    with _lock:
        if _started:
            return True
        try:
            from pynput.keyboard import GlobalHotKeys, Listener
        except Exception as exc:
            logger.error("Cannot start hotkey listener: %s", exc)
            return False

        bindings = {
            type_hotkey: _make_handler_type(),
            abort_hotkey: _make_handler_abort(),
        }
        try:
            _listener = GlobalHotKeys(bindings)
            _listener.daemon = True
            _listener.start()

            _diag_listener = Listener(on_press=_diagnostic_on_press)
            _diag_listener.daemon = True
            _diag_listener.start()

            _first_key_seen = False
            _started = True
            _started_at = time.monotonic()

            warn_thread = threading.Thread(
                target=_accessibility_warning_thread,
                name="hotkey-acc-check",
                daemon=True,
            )
            warn_thread.start()

            logger.info(
                "Hotkey listener started: type=%s abort=%s",
                type_hotkey,
                abort_hotkey,
            )
            return True
        except Exception as exc:
            logger.error("Failed to start hotkey listener: %s", exc)
            _listener = None
            _diag_listener = None
            return False


def stop_hotkey_listener() -> None:
    global _listener, _diag_listener, _started
    with _lock:
        for lst in (_listener, _diag_listener):
            if lst is not None:
                try:
                    lst.stop()
                except Exception:  # pragma: no cover
                    pass
        _listener = None
        _diag_listener = None
        _started = False
