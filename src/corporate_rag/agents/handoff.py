import base64
import hashlib
import hmac
import json
import time
from http.cookies import SimpleCookie
from typing import Any

from corporate_rag.auth.models import AuthUser
from corporate_rag.settings import AgentSettings, AuthSettings


class InvalidHandoffTokenError(ValueError):
    pass


def create_handoff_token(
    user: AuthUser,
    *,
    auth_settings: AuthSettings,
    agent_settings: AgentSettings,
) -> str:
    now = int(time.time())
    payload = {
        "sub": user.id,
        "username": user.username,
        "iat": now,
        "exp": now + agent_settings.handoff_token_ttl_seconds,
    }
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(encoded_payload, auth_settings.secret_key)
    return f"{encoded_payload}.{signature}"


def verify_handoff_token(token: str, *, auth_settings: AuthSettings) -> dict[str, str]:
    try:
        encoded_payload, signature = token.split(".", maxsplit=1)
    except ValueError as exc:
        raise InvalidHandoffTokenError("invalid token shape") from exc

    expected_signature = _sign(encoded_payload, auth_settings.secret_key)
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidHandoffTokenError("invalid token signature")

    try:
        payload = json.loads(_base64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidHandoffTokenError("invalid token payload") from exc

    if not isinstance(payload, dict):
        raise InvalidHandoffTokenError("invalid token payload")
    if int(payload.get("exp") or 0) < int(time.time()):
        raise InvalidHandoffTokenError("expired handoff token")

    user_id = _required_string(payload, "sub")
    username = _required_string(payload, "username")
    return {"id": user_id, "username": username}


def handoff_token_from_cookie(cookie_header: str, cookie_name: str) -> str | None:
    if not cookie_header:
        return None
    cookie = SimpleCookie()
    cookie.load(cookie_header)
    morsel = cookie.get(cookie_name)
    if morsel is None:
        return None
    return morsel.value


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise InvalidHandoffTokenError(f"missing token field {key!r}")
    return value


def _sign(encoded_payload: str, secret_key: str) -> str:
    digest = hmac.new(secret_key.encode(), encoded_payload.encode(), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _base64url_decode(value: str) -> str:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode()).decode()
