import base64
import hashlib
import hmac
import json
import time
from typing import Any

from corporate_rag.auth.models import AuthUser


class InvalidTokenError(ValueError):
    pass


def create_access_token(user: AuthUser, secret_key: str, ttl_seconds: int) -> str:
    now = int(time.time())
    payload = {
        "sub": user.id,
        "username": user.username,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    encoded_payload = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(encoded_payload, secret_key)
    return f"{encoded_payload}.{signature}"


def verify_access_token(token: str, secret_key: str) -> dict[str, Any]:
    try:
        encoded_payload, signature = token.split(".", maxsplit=1)
    except ValueError as exc:
        raise InvalidTokenError("invalid token") from exc

    expected_signature = _sign(encoded_payload, secret_key)
    if not hmac.compare_digest(signature, expected_signature):
        raise InvalidTokenError("invalid token")

    try:
        raw_payload = json.loads(_urlsafe_b64decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidTokenError("invalid token") from exc
    if not isinstance(raw_payload, dict):
        raise InvalidTokenError("invalid token")
    payload: dict[str, Any] = raw_payload

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(time.time()):
        raise InvalidTokenError("token expired")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError("invalid token")

    return payload


def _sign(encoded_payload: str, secret_key: str) -> str:
    digest = hmac.new(
        secret_key.encode(),
        encoded_payload.encode(),
        hashlib.sha256,
    ).digest()
    return _urlsafe_b64encode(digest)


def _urlsafe_b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))
