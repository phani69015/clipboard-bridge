"""Command-line interface for clipboard-bridge.

Subcommands:
- run         Start the HTTP server and (by default) the autotyper hotkey.
- stop        Stop a running server (sends SIGTERM via PID file).
- status      Show whether a server is running, plus URL and PIN.
- pin         Print the persisted PIN without starting the server.
- regen-pin   Regenerate and persist a new PIN.

Top-level:
- --version   Print the package version.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time

from . import config
from .__version__ import __version__

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
DEFAULT_TYPE_HOTKEY = "<ctrl>+a"
DEFAULT_ABORT_HOTKEY = "<esc>"

STOP_TIMEOUT_SEC = 5.0
STOP_POLL_INTERVAL = 0.1


def _format_hotkey_display(hk: str) -> str:
    """Make pynput hotkey strings look nicer in the banner."""
    replacements = {
        "<cmd>": "Cmd",
        "<shift>": "Shift",
        "<ctrl>": "Ctrl",
        "<alt>": "Option",
        "<esc>": "Esc",
    }
    out = hk
    for k, v in replacements.items():
        out = out.replace(k, v)
    return out.strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cb-bridge",
        description="Clipboard Bridge + Autotyper (phone -> computer over LAN).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"clipboard-bridge {__version__}",
    )

    sub = parser.add_subparsers(dest="command")

    # run (default)
    p_run = sub.add_parser("run", help="Start the server (default).")
    p_run.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind address (default: {DEFAULT_HOST}).",
    )
    p_run.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT}).",
    )
    p_run.add_argument(
        "--no-hotkey",
        action="store_true",
        help="Disable the global autotyper hotkey listener.",
    )
    p_run.add_argument(
        "--hotkey",
        default=DEFAULT_TYPE_HOTKEY,
        help=(
            "Hotkey that triggers autotyping. Uses pynput syntax, "
            f'e.g. "<ctrl>+a" (default: {DEFAULT_TYPE_HOTKEY}).'
        ),
    )
    p_run.add_argument(
        "--abort-key",
        default=DEFAULT_ABORT_HOTKEY,
        help=(
            "Hotkey that aborts an in-progress autotype "
            f"(default: {DEFAULT_ABORT_HOTKEY})."
        ),
    )

    sub.add_parser("stop", help="Stop a running server.")
    sub.add_parser("status", help="Show whether a server is running.")
    sub.add_parser("pin", help="Print the persisted PIN and exit.")
    sub.add_parser("regen-pin", help="Generate and persist a new PIN.")

    return parser


def _cmd_pin() -> int:
    pin = config.load_pin()
    print(pin)
    return 0


def _cmd_regen_pin() -> int:
    pin = config.regen_pin()
    print(f"New PIN: {pin}")
    print(f"Stored at: {config.config_file()}")
    return 0


def _cmd_status() -> int:
    pid = config.running_pid()
    if pid is None:
        print("clipboard-bridge: not running")
        return 1
    print(f"clipboard-bridge: running (PID {pid})")
    print(f"PID file: {config.pid_file()}")
    print(f"PIN     : {config.load_pin()}")
    return 0


def _cmd_stop() -> int:
    pid = config.running_pid()
    if pid is None:
        print("clipboard-bridge: not running.")
        return 1

    print(f"Stopping clipboard-bridge (PID {pid})...")
    try:
        if sys.platform == "win32":
            # On Windows, SIGTERM is mapped to TerminateProcess; SIGINT
            # only works for processes that share a console. SIGTERM is
            # the most reliable for our use case.
            os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        print("Process already gone.")
        config.clear_pid()
        return 0
    except PermissionError:
        print(
            f"Permission denied when signaling PID {pid}. "
            "The server may be running as a different user."
        )
        return 2

    # Wait up to STOP_TIMEOUT_SEC for the process to die gracefully.
    deadline = time.monotonic() + STOP_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if config.running_pid() is None:
            print("Stopped.")
            return 0
        time.sleep(STOP_POLL_INTERVAL)

    # Still alive — escalate to SIGKILL on Unix (Windows: SIGTERM was
    # already a hard terminate, so just give up).
    print(f"Server didn't exit within {STOP_TIMEOUT_SEC:.0f}s.")
    if sys.platform != "win32":
        print("Sending SIGKILL...")
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        time.sleep(0.3)

    if config.running_pid() is None:
        config.clear_pid()
        print("Stopped.")
        return 0
    print("Failed to stop the server. PID file left in place.")
    return 3


def _cmd_run(args: argparse.Namespace) -> int:
    # Imports are deferred so `pin`/`regen-pin`/`--version` don't pay the
    # cost of loading Flask, pynput, etc.
    from . import create_app, start_background_services
    from .startup import get_local_ip, get_mdns_hostname, print_banner

    # Refuse to start if another instance is already running.
    existing = config.running_pid()
    if existing is not None:
        print(
            f"clipboard-bridge is already running (PID {existing}).\n"
            "Use 'cb-bridge stop' first, or 'cb-bridge status' to check.",
            file=sys.stderr,
        )
        return 1

    app = create_app()

    hostname = get_mdns_hostname()
    ip = get_local_ip()
    hostname_url = f"http://{hostname}:{args.port}"
    ip_url = f"http://{ip}:{args.port}"

    print_banner(hostname_url, ip_url, app.config["PIN"])

    started, message = start_background_services(
        enable_hotkey=not args.no_hotkey,
        type_hotkey=args.hotkey,
        abort_hotkey=args.abort_key,
    )
    if not args.no_hotkey:
        type_disp = _format_hotkey_display(args.hotkey)
        abort_disp = _format_hotkey_display(args.abort_key)
        if started:
            print(f" Autotyper hotkey: {type_disp}   Abort: {abort_disp}")
            print(
                " (If the hotkey doesn't fire, grant Accessibility permission to "
                "your terminal\n"
                "  in System Settings -> Privacy & Security -> Accessibility, "
                "then restart.)"
            )
        else:
            print(f" [!] Autotyper hotkey unavailable: {message}")
    else:
        print(" Autotyper hotkey: disabled (--no-hotkey)")
    print(" Stop with Ctrl+C, or from any other terminal: cb-bridge stop")
    print()

    # Write the PID so `cb-bridge stop` and `cb-bridge status` can find us.
    config.write_pid()

    # Translate SIGTERM (from `cb-bridge stop`) into a clean shutdown.
    # Werkzeug's dev server doesn't have a public "stop" hook, so the
    # cleanest approach is to raise SystemExit here, which the dev
    # server's signal handlers cooperate with.
    def _handle_term(_signum, _frame):
        raise SystemExit(0)

    try:
        signal.signal(signal.SIGTERM, _handle_term)
    except (ValueError, OSError):
        # Not on the main thread, or platform doesn't support — ignore.
        pass

    try:
        # Disable Flask's reloader so the PIN doesn't regenerate twice on boot.
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        config.clear_pid()
        print("\nclipboard-bridge stopped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Default subcommand is "run".
    command = args.command or "run"

    if command == "pin":
        return _cmd_pin()
    if command == "regen-pin":
        return _cmd_regen_pin()
    if command == "stop":
        return _cmd_stop()
    if command == "status":
        return _cmd_status()
    if command == "run":
        # If no subcommand was given, args won't have run-specific
        # attributes; fill defaults.
        if args.command is None:
            args.host = DEFAULT_HOST
            args.port = DEFAULT_PORT
            args.no_hotkey = False
            args.hotkey = DEFAULT_TYPE_HOTKEY
            args.abort_key = DEFAULT_ABORT_HOTKEY
        return _cmd_run(args)

    parser.error(f"Unknown command: {command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
