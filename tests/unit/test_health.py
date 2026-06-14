from fastapi.testclient import TestClient

from corporate_rag.app.main import create_app
from corporate_rag.settings import AppSettings
from tests.unit.auth_helpers import authenticated_client


def test_health_returns_application_status() -> None:
    settings = AppSettings(app_name="Test Corporate RAG", environment="test")
    client = authenticated_client(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "Test Corporate RAG",
        "environment": "test",
    }


def test_health_requires_authentication() -> None:
    settings = AppSettings(app_name="Test Corporate RAG", environment="test")
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 401
