"""Clipboard access. Thin wrapper around pyperclip.

On macOS, pyperclip shells out to the system `pbcopy`/`pbpaste` binaries,
which is the standard, well-behaved way to interact with the pasteboard.
"""

from __future__ import annotations

import pyperclip


class ClipboardError(RuntimeError):
    """Raised when the underlying clipboard backend fails."""


def set_clipboard(text: str) -> None:
    """Write text to the system clipboard. UTF-8 is preserved as-is."""
    if not isinstance(text, str):
        raise ClipboardError("Text must be a string.")
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as exc:  # pragma: no cover
        raise ClipboardError(f"Clipboard backend failed: {exc}") from exc
