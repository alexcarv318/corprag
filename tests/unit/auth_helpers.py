from fastapi import FastAPI
from fastapi.testclient import TestClient

from corporate_rag.auth.models import AuthUser
from corporate_rag.auth.password import hash_password, verify_password
from corporate_rag.auth.tokens import create_access_token
from corporate_rag.settings import AuthSettings

TEST_AUTH = ("alice", "correct horse battery staple")
TEST_AUTH_SETTINGS = AuthSettings(signup_key="secret", secret_key="test-secret")


class FakeAuthRepository:
    def __init__(self) -> None:
        self.user = AuthUser(
            id="user-1",
            username=TEST_AUTH[0],
            password_hash=hash_password(TEST_AUTH[1]),
        )

    def authenticate(self, username: str, password: str) -> AuthUser | None:
        if username == self.user.username and verify_password(password, self.user.password_hash):
            return self.user
        return None

    def get_user(self, user_id: str) -> AuthUser | None:
        return self.user if user_id == self.user.id else None


def authenticated_client(app: FastAPI) -> TestClient:
    repository = FakeAuthRepository()
    app.state.auth_repository = repository
    app.state.auth_settings = TEST_AUTH_SETTINGS
    client = TestClient(app)
    token = create_access_token(
        repository.user,
        secret_key=TEST_AUTH_SETTINGS.secret_key,
        ttl_seconds=TEST_AUTH_SETTINGS.access_token_ttl_seconds,
    )
    client.headers["Authorization"] = f"Bearer {token}"
    return client
