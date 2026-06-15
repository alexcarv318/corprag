from pathlib import Path

import pytest

from corporate_rag.settings import (
    AgentSettings,
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    Neo4jSettings,
)


@pytest.fixture(autouse=True)
def clear_settings_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    environment_keys = (
        "CORPORATE_RAG_APP_NAME",
        "CORPORATE_RAG_ENVIRONMENT",
        "CORPORATE_RAG_LOG_LEVEL",
        "CORPORATE_RAG_API_PREFIX",
        "CORPORATE_RAG_CORS_ORIGINS",
        "CORPORATE_RAG_DATABASE_URL",
        "CORPORATE_RAG_DATABASE_POOL_MIN_SIZE",
        "CORPORATE_RAG_DATABASE_POOL_MAX_SIZE",
        "CORPORATE_RAG_AUTH_SIGNUP_KEY",
        "CORPORATE_RAG_AGENT_CORPORATE_MCP_TRANSPORT",
        "CORPORATE_RAG_AGENT_CORPORATE_MCP_URL",
        "CORPORATE_RAG_AGENT_LAW_MCP_TRANSPORT",
        "CORPORATE_RAG_AGENT_LAW_MCP_URL",
        "CORPORATE_RAG_AGENT_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "CORPORATE_RAG_NEO4J_URI",
        "CORPORATE_RAG_NEO4J_USER",
        "CORPORATE_RAG_NEO4J_PASSWORD",
        "CORPORATE_RAG_NEO4J_CORPORATE_DATABASE",
        "CORPORATE_RAG_NEO4J_LAW_DATABASE",
        "CORPORATE_RAG_NEO4J_MAX_CONNECTION_LIFETIME_SECONDS",
        "CORPORATE_RAG_NEO4J_CONNECTION_ACQUISITION_TIMEOUT_SECONDS",
        "CORPORATE_RAG_NEO4J_CONNECTION_TIMEOUT_SECONDS",
        "CORPORATE_RAG_NEO4J_KEEP_ALIVE",
        "CORPORATE_RAG_NEO4J_NOTIFICATIONS_MIN_SEVERITY",
    )
    for key in environment_keys:
        monkeypatch.delenv(key, raising=False)


def test_app_settings_defaults_are_local() -> None:
    settings = AppSettings()

    assert settings.app_name == "Corporate RAG"
    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.api_prefix == "/api"
    assert settings.cors_origins == ()


def test_app_settings_accept_explicit_values() -> None:
    settings = AppSettings(
        app_name="Custom App",
        environment="test",
        log_level="DEBUG",
        api_prefix="/custom-api",
        cors_origins=("http://localhost:5173",),
    )

    assert settings.app_name == "Custom App"
    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"
    assert settings.api_prefix == "/custom-api"
    assert settings.cors_origins == ("http://localhost:5173",)


def test_neo4j_settings_defaults_match_local_development() -> None:
    settings = Neo4jSettings()

    assert settings.uri == "bolt://localhost:7687"
    assert settings.user == "neo4j"
    assert settings.password == ""
    assert settings.corporate_database == "neo4j"
    assert settings.law_database == "law"
    assert settings.max_connection_lifetime_seconds == 300
    assert settings.connection_acquisition_timeout_seconds == 60.0
    assert settings.connection_timeout_seconds == 30.0
    assert settings.keep_alive is True
    assert settings.notifications_min_severity == "OFF"


def test_database_settings_defaults_match_local_development() -> None:
    settings = DatabaseSettings()

    assert settings.database_url == (
        "postgresql://corporate_rag:corporate_rag@localhost:5432/corporate_rag"
    )
    assert settings.database_pool_min_size == 1
    assert settings.database_pool_max_size == 5


def test_database_settings_accept_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORPORATE_RAG_DATABASE_URL", "postgresql://app:secret@db/app")
    monkeypatch.setenv("CORPORATE_RAG_DATABASE_POOL_MIN_SIZE", "2")
    monkeypatch.setenv("CORPORATE_RAG_DATABASE_POOL_MAX_SIZE", "10")

    settings = DatabaseSettings()

    assert settings.database_url == "postgresql://app:secret@db/app"
    assert settings.database_pool_min_size == 2
    assert settings.database_pool_max_size == 10


def test_auth_settings_default_disables_signup() -> None:
    settings = AuthSettings()

    assert settings.signup_key is None


def test_auth_settings_accept_signup_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORPORATE_RAG_AUTH_SIGNUP_KEY", "secret")

    settings = AuthSettings()

    assert settings.signup_key == "secret"


def test_agent_settings_defaults_match_local_mcp_services() -> None:
    settings = AgentSettings()

    assert settings.corporate_mcp_transport == "streamable_http"
    assert settings.corporate_mcp_url == "http://127.0.0.1:18800/mcp/"
    assert settings.law_mcp_transport == "streamable_http"
    assert settings.law_mcp_url == "http://127.0.0.1:18801/mcp/"


def test_agent_settings_accept_mcp_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORPORATE_RAG_AGENT_CORPORATE_MCP_TRANSPORT", "streamable_http")
    monkeypatch.setenv("CORPORATE_RAG_AGENT_CORPORATE_MCP_URL", "http://mcp-neo4j:8000/mcp/")
    monkeypatch.setenv("CORPORATE_RAG_AGENT_LAW_MCP_TRANSPORT", "streamable_http")
    monkeypatch.setenv("CORPORATE_RAG_AGENT_LAW_MCP_URL", "http://mcp-law:8000/mcp/")

    settings = AgentSettings()

    assert settings.corporate_mcp_url == "http://mcp-neo4j:8000/mcp/"
    assert settings.law_mcp_url == "http://mcp-law:8000/mcp/"


def test_neo4j_settings_accept_explicit_values() -> None:
    settings = Neo4jSettings(
        uri="neo4j+s://graph.example.test",
        user="app",
        password="secret",
        corporate_database="corporate",
        law_database="law_prod",
        max_connection_lifetime_seconds=120,
        connection_acquisition_timeout_seconds=10.0,
        connection_timeout_seconds=5.0,
        keep_alive=False,
        notifications_min_severity=None,
    )

    assert settings.uri == "neo4j+s://graph.example.test"
    assert settings.user == "app"
    assert settings.password == "secret"
    assert settings.corporate_database == "corporate"
    assert settings.law_database == "law_prod"
    assert settings.max_connection_lifetime_seconds == 120
    assert settings.connection_acquisition_timeout_seconds == 10.0
    assert settings.connection_timeout_seconds == 5.0
    assert settings.keep_alive is False
    assert settings.notifications_min_severity is None


def test_neo4j_settings_accept_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_URI", "neo4j+s://graph.example.test")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_USER", "app")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_PASSWORD", "secret")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_CORPORATE_DATABASE", "corporate")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_LAW_DATABASE", "law_prod")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_MAX_CONNECTION_LIFETIME_SECONDS", "90")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_CONNECTION_ACQUISITION_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_CONNECTION_TIMEOUT_SECONDS", "6.5")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_KEEP_ALIVE", "false")
    monkeypatch.setenv("CORPORATE_RAG_NEO4J_NOTIFICATIONS_MIN_SEVERITY", "WARNING")

    settings = Neo4jSettings()

    assert settings.uri == "neo4j+s://graph.example.test"
    assert settings.user == "app"
    assert settings.password == "secret"
    assert settings.corporate_database == "corporate"
    assert settings.law_database == "law_prod"
    assert settings.max_connection_lifetime_seconds == 90
    assert settings.connection_acquisition_timeout_seconds == 12.5
    assert settings.connection_timeout_seconds == 6.5
    assert settings.keep_alive is False
    assert settings.notifications_min_severity == "WARNING"
