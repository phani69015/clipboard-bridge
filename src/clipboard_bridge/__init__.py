"""Flask application factory."""

from __future__ import annotations

from flask import Flask

from . import auth, config
from .routes import bp

MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

    # Persistent PIN: generated on first run, reused on subsequent runs.
    pin = config.load_pin()
    auth.set_pin(pin)
    app.config["PIN"] = pin

    app.register_blueprint(bp)
    return app


def start_background_services(
    enable_hotkey: bool,
    type_hotkey: str,
    abort_hotkey: str,
) -> tuple[bool, str]:
    """Start the autotyper hotkey listener if requested."""
    if not enable_hotkey:
        return False, "Hotkey disabled by --no-hotkey."

    from . import hotkey

    started = hotkey.start_hotkey_listener(type_hotkey, abort_hotkey)
    if started:
        return True, "Hotkey listener active."
    return False, (
        "Hotkey listener failed to start. "
        "Check that pynput is installed and that the terminal has "
        "Accessibility permission "
        "(System Settings -> Privacy & Security -> Accessibility)."
    )
