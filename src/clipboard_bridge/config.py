"""Persistent configuration: PIN storage in an OS-correct config dir.

The config file is JSON, stored at:
- macOS:   ~/Library/Application Support/clipboard-bridge/config.json
- Linux:   ~/.config/clipboard-bridge/config.json
- Windows: %APPDATA%\\clipboard-bridge\\config.json

A PIN is generated lazily on first use and persisted; subsequent runs
reuse it. Use `regen_pin()` (CLI: `cb-bridge regen-pin`) to rotate.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
import tempfile
from pathlib import Path

from platformdirs import user_config_dir

APP_NAME = "clipboard-bridge"
CONFIG_FILENAME = "config.json"
PID_FILENAME = "server.pid"


def config_dir() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False))


def config_file() -> Path:
    return config_dir() / CONFIG_FILENAME


def pid_file() -> Path:
    return config_dir() / PID_FILENAME


def _generate_pin() -> str:
    return f"{secrets.randbelow(10_000):04d}"


def _read_config() -> dict:
    path = config_file()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _write_config_atomic(data: dict) -> None:
    """Write the config JSON atomically, then chmod 600 on Unix."""
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = config_file()

    # Write to a temp file in the same dir, then rename for atomicity.
    fd, tmp_path = tempfile.mkstemp(
        prefix=".config-", suffix=".tmp", dir=str(directory)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Best-effort restrictive permissions on Unix; harmless no-op on Windows.
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def load_pin() -> str:
    """Return the persisted PIN, generating and saving one if missing."""
    data = _read_config()
    pin = data.get("pin")
    if isinstance(pin, str) and len(pin) == 4 and pin.isdigit():
        return pin
    pin = _generate_pin()
    data["pin"] = pin
    _write_config_atomic(data)
    return pin


def regen_pin() -> str:
    """Generate a new PIN, persist it, and return it."""
    data = _read_config()
    pin = _generate_pin()
    data["pin"] = pin
    _write_config_atomic(data)
    return pin


# ---------------------------------------------------------------------------
# PID file (used by `cb-bridge stop` and `cb-bridge status`)
# ---------------------------------------------------------------------------

def _pid_alive(pid: int) -> bool:
    """Return True if a process with this PID is currently running."""
    if pid <= 0:
        return False
    try:
        # Signal 0 doesn't actually send a signal; it just probes.
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by someone else.
        return True
    except OSError:
        return False


def write_pid(pid: int | None = None) -> None:
    """Write the current (or given) PID to the PID file."""
    if pid is None:
        pid = os.getpid()
    directory = config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = pid_file()
    with path.open("w", encoding="utf-8") as f:
        f.write(f"{pid}\n")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def read_pid() -> int | None:
    """Return the PID stored in the PID file, or None if missing/invalid."""
    path = pid_file()
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8").strip()
        return int(text)
    except (OSError, ValueError):
        return None


def clear_pid() -> None:
    """Remove the PID file if present."""
    try:
        pid_file().unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass


def running_pid() -> int | None:
    """Return the PID of a live server, or None.

    Cleans up a stale PID file if found.
    """
    pid = read_pid()
    if pid is None:
        return None
    if _pid_alive(pid):
        return pid
    # Stale file (server crashed or was killed without cleanup).
    clear_pid()
    return None
