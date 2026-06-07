"""Startup helpers: detect host info, render QR code, print banner."""

from __future__ import annotations

import io
import socket

import qrcode

from .__version__ import __version__


def get_local_ip() -> str:
    """Return the primary LAN IPv4 address of this machine.

    Uses the standard UDP-socket trick: open a non-routed UDP socket to a
    public IP; the kernel picks the outbound interface and we read its
    local address. No packets are actually sent.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def get_mdns_hostname() -> str:
    """Return `<hostname>.local` (Bonjour) form for this Mac."""
    name = socket.gethostname()
    # macOS hostname may already include `.local`. Normalize.
    if name.endswith(".local"):
        return name
    # Strip any other domain suffix and append `.local`.
    short = name.split(".")[0]
    return f"{short}.local"


def _qr_ascii(url: str) -> str:
    """Render a URL as an ASCII QR code suitable for terminal display."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    buf = io.StringIO()
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()


def print_banner(hostname_url: str, ip_url: str, pin: str) -> None:
    bar = "━" * 60
    print()
    print(bar)
    print(f" Clipboard Bridge v{__version__}")
    print()
    print(f"   URL  : {ip_url}")
    print(f"   Alt  : {hostname_url}   (only if your network supports mDNS)")
    print(f"   PIN  : {pin}")
    print()
    print(" (PIN persists across restarts. Run \"cb-bridge regen-pin\" to rotate.)")
    print()
    print(" Scan this QR code with your phone camera:")
    print()
    # Encode the IP URL — works on every network, including ones that
    # don't resolve `.local` hostnames.
    print(_qr_ascii(ip_url))
    print(" Press Ctrl+C to stop.")
    print(bar)
    print()
