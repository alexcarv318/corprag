from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from corporate_rag.app.main import create_app
from corporate_rag.auth.models import AuthUser
from corporate_rag.auth.password import hash_password, verify_password
from corporate_rag.auth.repository import (
    AuthRepository,
    InvalidPasswordError,
    InvalidUsernameError,
)
from corporate_rag.auth.tokens import create_access_token
from corporate_rag.settings import AppSettings, AuthSettings


class FakeCursor:
    def __init__(self, row: tuple[str, str, str] | None) -> None:
        self.row = row

    def fetchone(self) -> tuple[str, str, str] | None:
        return self.row


class FakeConnection:
    def __init__(self, rows: dict[str, tuple[str, str, str]]) -> None:
        self.rows = rows
        self.inserts: list[tuple[str, str, str]] = []

    def execute(self, query: str, parameters: tuple[Any, ...]) -> FakeCursor:
        if query.lstrip().startswith("INSERT"):
            user_id, username, password_hash = parameters
            self.inserts.append((str(user_id), str(username), str(password_hash)))
            self.rows[str(username)] = (str(user_id), str(username), str(password_hash))
            return FakeCursor(None)

        username = str(parameters[0])
        return FakeCursor(self.rows.get(username))


class FakePool:
    def __init__(self) -> None:
        self.rows: dict[str, tuple[str, str, str]] = {}
        self.connection_instance = FakeConnection(self.rows)

    @contextmanager
    def connection(self) -> Iterator[FakeConnection]:
        yield self.connection_instance


class FakeAuthRepository:
    def __init__(self) -> None:
        self.user = AuthUser(
            id="user-1",
            username="alice",
            password_hash=hash_password("correct horse battery staple"),
        )

    def create_user(self, username: str, password: str) -> AuthUser:
        return AuthUser(id="user-2", username=username.strip().lower(), password_hash=password)

    def authenticate(self, username: str, password: str) -> AuthUser | None:
        if username == "alice" and password == "correct horse battery staple":
            return self.user
        return None

    def get_user(self, user_id: str) -> AuthUser | None:
        return self.user if user_id == self.user.id else None


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash) is True
    assert verify_password("wrong password", password_hash) is False
    assert verify_password("password", "not-a-valid-hash") is False


def test_repository_creates_and_authenticates_user() -> None:
    repository = AuthRepository(FakePool())

    user = repository.create_user(" Alice.Admin ", "correct horse battery staple")

    assert user.username == "alice.admin"
    assert repository.authenticate("alice.admin", "correct horse battery staple") == user
    assert repository.authenticate("alice.admin", "wrong password") is None


def test_repository_validates_username_and_password() -> None:
    repository = AuthRepository(FakePool())

    try:
        repository.create_user("No", "correct horse battery staple")
    except InvalidUsernameError:
        pass
    else:
        raise AssertionError("Expected InvalidUsernameError")

    try:
        repository.create_user("alice", "short")
    except InvalidPasswordError:
        pass
    else:
        raise AssertionError("Expected InvalidPasswordError")


def build_auth_client(
    repository: FakeAuthRepository | None = None,
    auth_settings: AuthSettings | None = None,
) -> TestClient:
    app = create_app(AppSettings(environment="test"), configure_workflows=False)
    app.state.auth_repository = repository or FakeAuthRepository()
    app.state.auth_settings = auth_settings or AuthSettings(
        signup_key="secret",
        secret_key="test-secret",
    )
    return TestClient(app)


def test_signup_requires_configured_signup_key() -> None:
    client = build_auth_client(auth_settings=AuthSettings(signup_key=None))

    response = client.post(
        "/api/auth/sign-up",
        json={
            "username": "alice",
            "password": "correct horse battery staple",
            "signup_key": "secret",
        },
    )

    assert response.status_code == 404


def test_signup_requires_matching_signup_key() -> None:
    client = build_auth_client()

    response = client.post(
        "/api/auth/sign-up",
        json={
            "username": "alice",
            "password": "correct horse battery staple",
            "signup_key": "wrong",
        },
    )

    assert response.status_code == 403


def test_signup_creates_user_with_valid_signup_key() -> None:
    client = build_auth_client()

    response = client.post(
        "/api/auth/sign-up",
        json={
            "username": " Alice ",
            "password": "correct horse battery staple",
            "signup_key": "secret",
        },
    )

    assert response.status_code == 201
    assert response.json() == {"id": "user-2", "username": "alice"}
    assert response.headers["cache-control"] == "no-store"


def test_sign_in_returns_bearer_token() -> None:
    client = build_auth_client()

    response = client.post(
        "/api/auth/sign-in",
        json={"username": "alice", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]
    assert response.json()["user"] == {"id": "user-1", "username": "alice"}


def test_sign_in_rejects_wrong_password() -> None:
    client = build_auth_client()

    response = client.post(
        "/api/auth/sign-in",
        json={"username": "alice", "password": "wrong password"},
    )

    assert response.status_code == 401


def test_me_returns_current_bearer_token_user() -> None:
    auth_settings = AuthSettings(signup_key="secret", secret_key="test-secret")
    repository = FakeAuthRepository()
    client = build_auth_client(repository=repository, auth_settings=auth_settings)
    token = create_access_token(
        repository.user,
        secret_key=auth_settings.secret_key,
        ttl_seconds=auth_settings.access_token_ttl_seconds,
    )

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"id": "user-1", "username": "alice"}


def test_me_rejects_missing_token() -> None:
    client = build_auth_client()

    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Bearer realm="corporate-rag"'
