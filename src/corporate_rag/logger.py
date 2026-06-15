import json
import logging
from typing import Any

from corporate_rag.auth.models import AuthUser

LOGGER_NAME = "corporate_rag.user"
MAX_TEXT_LENGTH = 4000
SENSITIVE_KEYS = {
    "access_token",
    "authorization",
    "cookie",
    "handoff_token",
    "password",
    "secret",
    "secret_key",
    "signup_key",
    "token",
}


def configure_logging(level: str = "INFO") -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level.upper())
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(filename)s:%(funcName)s:%(lineno)d %(message)s"
    )
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return

    for handler in logger.handlers:
        handler.setFormatter(formatter)


def log_user_logged_in(user: AuthUser) -> None:
    _logger().info("User %s logged in", _user_label(user), stacklevel=2)


def log_user_logged_out(user: AuthUser) -> None:
    _logger().info("User %s logged out", _user_label(user), stacklevel=2)


def log_user_ran_workflow(user: AuthUser, workflow_id: str, parameters: dict[str, Any]) -> None:
    _logger().info(
        "User %s ran workflows %s with paramets:\n%s",
        _user_label(user),
        workflow_id,
        _json_dump(_redact(parameters)),
        stacklevel=2,
    )


def log_user_ran_agent(user: Any, agent_name: str, question: str) -> None:
    _logger().info(
        'User %s run "%s" agent with question: "%s"',
        _chainlit_user_label(user),
        agent_name,
        _truncate(question),
        stacklevel=2,
    )


def log_user_got_response(user: Any, response: str) -> None:
    _logger().info(
        'User %s got response:\n"%s"',
        _chainlit_user_label(user),
        _truncate(response),
        stacklevel=2,
    )


def _logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def _user_label(user: AuthUser) -> str:
    return user.username or user.id


def _chainlit_user_label(user: Any) -> str:
    display_name = getattr(user, "display_name", None)
    if display_name:
        return str(display_name)
    metadata = getattr(user, "metadata", None)
    if isinstance(metadata, dict) and metadata.get("username"):
        return str(metadata["username"])
    identifier = getattr(user, "identifier", None) or getattr(user, "id", None)
    return str(identifier or "unknown")


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if _is_sensitive_key(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _truncate(value)
    return value


def _is_sensitive_key(key: Any) -> bool:
    lowered = str(key).lower()
    return any(sensitive in lowered for sensitive in SENSITIVE_KEYS)


def _truncate(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) <= MAX_TEXT_LENGTH:
        return cleaned
    return f"{cleaned[:MAX_TEXT_LENGTH]}... [truncated]"


def _json_dump(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=True, indent=2, sort_keys=True)
