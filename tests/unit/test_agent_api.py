import os

import pytest
from fastapi.testclient import TestClient

from corporate_rag.agents.handoff import verify_handoff_token
from corporate_rag.app.main import create_app
from corporate_rag.settings import AgentSettings, AppSettings
from tests.unit.auth_helpers import TEST_AUTH_SETTINGS, authenticated_client


def build_agent_client() -> TestClient:
    app = create_app(AppSettings(environment="test"), configure_workflows=False)
    app.state.agent_settings = AgentSettings(
        chainlit_mount_path="/agent-runtime",
        handoff_cookie_name="agent-handoff",
        handoff_token_ttl_seconds=30,
        default_model_id="openai:gpt-4.1",
    )
    return authenticated_client(app)


def test_agent_config_returns_product_ui_contract() -> None:
    client = build_agent_client()

    response = client.get("/api/agent/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_path"] == "/agent-runtime"
    assert payload["default_mode"] == "corporate"
    assert payload["default_model_id"] == "openai:gpt-4.1"
    assert {mode["id"] for mode in payload["modes"]} == {"corporate", "law"}
    assert payload["starters"]["corporate"]
    assert payload["starters"]["law"]


def test_agent_handoff_sets_runtime_scoped_cookie() -> None:
    client = build_agent_client()

    response = client.post("/api/agent/handoff")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "runtime_path": "/agent-runtime",
        "header_auth_path": "/agent-runtime/auth/header",
        "websocket_path": "/agent-runtime/ws/socket.io",
        "expires_in_seconds": 30,
    }
    cookie_header = response.headers["set-cookie"]
    assert "agent-handoff=" in cookie_header
    assert "Path=/agent-runtime" in cookie_header
    token = response.cookies["agent-handoff"]
    assert verify_handoff_token(token, auth_settings=TEST_AUTH_SETTINGS) == {
        "id": "user-1",
        "username": "alice",
    }


def test_chainlit_runtime_stays_off_builtin_database_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://chainlit:secret@db/chainlit")
    monkeypatch.setenv("CORPORATE_RAG_AUTH_SECRET_KEY", "short-test-secret")
    monkeypatch.delenv("CHAINLIT_AUTH_SECRET", raising=False)

    create_app(AppSettings(environment="test"), configure_workflows=False)

    assert "DATABASE_URL" not in os.environ
    assert len(os.environ["CHAINLIT_AUTH_SECRET"]) == 64
