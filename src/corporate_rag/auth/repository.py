import re
import uuid
from typing import Any, Protocol

from psycopg.errors import UniqueViolation

from corporate_rag.auth.models import AuthUser
from corporate_rag.auth.password import hash_password, verify_password

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


class AuthError(ValueError):
    pass


class DuplicateUsernameError(AuthError):
    pass


class InvalidUsernameError(AuthError):
    pass


class InvalidPasswordError(AuthError):
    pass


class ConnectionPool(Protocol):
    def connection(self) -> Any:
        raise NotImplementedError


class AuthRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def create_user(self, username: str, password: str) -> AuthUser:
        normalized_username = normalize_username(username)
        validate_username(normalized_username)
        validate_password(password)

        user = AuthUser(
            id=str(uuid.uuid4()),
            username=normalized_username,
            password_hash=hash_password(password),
        )

        try:
            with self.pool.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO users (id, username, password_hash)
                    VALUES (%s, %s, %s)
                    """,
                    (user.id, user.username, user.password_hash),
                )
        except UniqueViolation as exc:
            raise DuplicateUsernameError("That username already exists.") from exc

        return user

    def authenticate(self, username: str, password: str) -> AuthUser | None:
        normalized_username = normalize_username(username)

        with self.pool.connection() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash
                FROM users
                WHERE username = %s
                """,
                (normalized_username,),
            ).fetchone()

        if row is None:
            return None

        user = AuthUser(
            id=str(row[0]),
            username=str(row[1]),
            password_hash=str(row[2]),
        )
        if not verify_password(password, user.password_hash):
            return None

        return user

    def get_user(self, user_id: str) -> AuthUser | None:
        with self.pool.connection() as connection:
            row = connection.execute(
                """
                SELECT id, username, password_hash
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            return None

        return AuthUser(
            id=str(row[0]),
            username=str(row[1]),
            password_hash=str(row[2]),
        )


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_username(username: str) -> None:
    if not USERNAME_PATTERN.fullmatch(username):
        raise InvalidUsernameError(
            "Username must be 3-64 chars: lowercase letters, numbers, ., _, -."
        )


def validate_password(password: str) -> None:
    if len(password) < 8:
        raise InvalidPasswordError("Password must be at least 8 characters.")
