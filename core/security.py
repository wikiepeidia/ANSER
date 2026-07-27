"""Security helpers shared by routes and integrations."""
import ipaddress
import os
import socket
import uuid
from functools import wraps
from urllib.parse import urlparse

from flask import current_app, jsonify
from flask_login import current_user


LOCAL_ENVIRONMENTS = {"dev", "development", "test", "testing"}


def require_internal_admin(view_func):
    """Gate a route to only the team's own accounts (core.config.Config.
    INTERNAL_ADMIN_EMAILS) — separate from any customer-facing role system;
    this is for the ANSER team's own cross-app platform overview, never
    shown to shop-owner customers. Self-contained — checks login too."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        from core.config import Config
        if not current_user.is_authenticated:
            return jsonify({"success": False, "message": "Vui lòng đăng nhập"}), 401
        email = (getattr(current_user, "email", "") or "").strip().lower()
        if email not in Config.INTERNAL_ADMIN_EMAILS:
            return jsonify({"success": False, "message": "Không có quyền truy cập"}), 403
        return view_func(*args, **kwargs)
    return wrapped


def env_flag(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def is_local_environment(config_obj=None):
    env = (
        os.environ.get("FLASK_ENV")
        or os.environ.get("APP_ENV")
        or getattr(config_obj, "ENV", "")
        or ""
    ).strip().lower()
    return env in LOCAL_ENVIRONMENTS or bool(getattr(config_obj, "TESTING", False))


def safe_api_error(logger, message="Internal server error", status=500, exc=None):
    error_id = uuid.uuid4().hex[:12]
    if logger is not None and exc is not None:
        logger.error("%s [%s]: %s", message, error_id, exc, exc_info=True)
    payload = {"success": False, "message": message, "error_id": error_id}
    return jsonify(payload), status


def _stream_size(file_storage):
    stream = getattr(file_storage, "stream", None)
    if stream is None:
        return None
    try:
        current = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(current)
        return size
    except (OSError, AttributeError):
        return None


def validate_upload(file_storage, allowed_extensions, allowed_mimetypes, max_bytes=None):
    if file_storage is None:
        raise ValueError("No file uploaded")

    filename = (file_storage.filename or "").strip()
    if not filename:
        raise ValueError("No file selected")

    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in {ext.lower().lstrip(".") for ext in allowed_extensions}:
        raise ValueError("Unsupported file type")

    mimetype = (file_storage.mimetype or "").lower()
    normalized_mimes = {mime.lower() for mime in allowed_mimetypes}
    if mimetype and mimetype not in normalized_mimes:
        raise ValueError("Unsupported file type")

    limit = max_bytes or current_app.config.get("MAX_CONTENT_LENGTH")
    size = getattr(file_storage, "content_length", None) or _stream_size(file_storage)
    if limit and size and size > limit:
        raise ValueError("File is too large")

    return True


def _resolved_addresses(hostname):
    addresses = set()
    for family, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
        if family in (socket.AF_INET, socket.AF_INET6):
            addresses.add(sockaddr[0])
    return addresses


def validate_public_webhook_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Webhook URL must use http or https")
    if not parsed.hostname:
        raise ValueError("Webhook URL must include a host")

    addresses = _resolved_addresses(parsed.hostname)
    if not addresses:
        raise ValueError("Webhook host could not be resolved")

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError("Webhook destination is not allowed")

    return True
