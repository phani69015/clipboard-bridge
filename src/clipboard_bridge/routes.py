"""HTTP routes: index page, PIN verification, clipboard write, autotype."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from . import auth, autotype
from .clipboard import ClipboardError, set_clipboard

bp = Blueprint("main", __name__)

MAX_TEXT_BYTES = 1 * 1024 * 1024  # 1 MB (also enforced at Flask config level)


def _client_ip() -> str:
    # We're LAN-only; remote_addr is sufficient. No proxy assumed.
    return request.remote_addr or "unknown"


def _require_pin(payload: dict) -> tuple[bool, tuple]:
    """Returns (ok, error_response_tuple_if_not_ok)."""
    ip = _client_ip()

    if auth.is_locked_out(ip):
        return False, (
            jsonify(
                ok=False,
                error="Too many failed attempts. Try again in a minute.",
            ),
            429,
        )

    pin = payload.get("pin")
    if not isinstance(pin, str) or not pin:
        return False, (jsonify(ok=False, error="PIN is required."), 400)

    if not auth.validate_pin(pin):
        auth.register_failure(ip)
        return False, (jsonify(ok=False, error="Incorrect PIN."), 401)

    auth.clear_attempts(ip)
    return True, ()


@bp.get("/")
def index():
    return render_template("index.html")


@bp.post("/verify")
def verify():
    """Check PIN only. Used by the phone to confirm a stored PIN is still valid."""
    payload = request.get_json(silent=True) or {}
    ok, err = _require_pin(payload)
    if not ok:
        return err
    return jsonify(ok=True)


@bp.post("/clipboard")
def clipboard():
    payload = request.get_json(silent=True) or {}

    ok, err = _require_pin(payload)
    if not ok:
        return err

    text = payload.get("text")
    if not isinstance(text, str):
        return jsonify(ok=False, error="Text is required."), 400
    if not text:
        return jsonify(ok=False, error="Cannot send empty text."), 400
    if len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        return jsonify(ok=False, error="Text too large (max 1 MB)."), 400

    try:
        set_clipboard(text)
    except ClipboardError as exc:
        return jsonify(ok=False, error=str(exc)), 500

    return jsonify(ok=True, bytes=len(text.encode("utf-8")))


# ---------------------------------------------------------------------------
# Autotype routes
# ---------------------------------------------------------------------------

@bp.post("/autotype")
def autotype_queue():
    payload = request.get_json(silent=True) or {}
    ok, err = _require_pin(payload)
    if not ok:
        return err

    text = payload.get("text")
    speed = payload.get("speed", "normal")
    jitter = bool(payload.get("jitter", False))

    if not isinstance(text, str) or not text:
        return jsonify(ok=False, error="Text is required."), 400
    if not isinstance(speed, str):
        return jsonify(ok=False, error="Invalid speed."), 400

    try:
        autotype.queue(text, speed=speed, jitter=jitter)
    except autotype.AutotypeError as exc:
        # Conflict if currently typing; otherwise validation issue.
        msg = str(exc)
        code = 409 if "typing" in msg.lower() else 400
        return jsonify(ok=False, error=msg), code

    return jsonify(ok=True, status="queued", total=len(text))


@bp.post("/autotype/clear")
def autotype_clear():
    payload = request.get_json(silent=True) or {}
    ok, err = _require_pin(payload)
    if not ok:
        return err
    autotype.clear()
    return jsonify(ok=True)


@bp.errorhandler(413)
def too_large(_e):
    return jsonify(ok=False, error="Text too large (max 1 MB)."), 413
