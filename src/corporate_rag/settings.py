from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CORPORATE_RAG_NEO4J_",
        extra="ignore",
    )

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = ""
    corporate_database: str = "neo4j"
    law_database: str = "law"
    max_connection_lifetime_seconds: int = 300
    connection_acquisition_timeout_seconds: float = 60.0
    connection_timeout_seconds: float = 30.0
    keep_alive: bool = True


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CORPORATE_RAG_",
        extra="ignore",
    )

    app_name: str = "Corporate RAG"
    environment: str = "local"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    cors_origins: tuple[str, ...] = Field(default=())


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CORPORATE_RAG_",
        extra="ignore",
    )

    database_url: str = "postgresql://corporate_rag:corporate_rag@localhost:5432/corporate_rag"
    database_pool_min_size: int = 1
    database_pool_max_size: int = 5


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CORPORATE_RAG_AUTH_",
        extra="ignore",
    )

    signup_key: str | None = None
    secret_key: str = "local-dev-secret-change-me"
    access_token_ttl_seconds: int = 60 * 60 * 12


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CORPORATE_RAG_AGENT_",
        extra="ignore",
        populate_by_name=True,
    )

    default_model_id: str = "openai:gpt-5.4"
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CORPORATE_RAG_AGENT_OPENAI_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    chainlit_mount_path: str = "/agent-runtime"
    handoff_cookie_name: str = "corporate_rag_chainlit_handoff"
    handoff_token_ttl_seconds: int = 60
    secure_handoff_cookie: bool = False
    corporate_mcp_transport: str = "streamable_http"
    corporate_mcp_url: str = "http://127.0.0.1:18800/mcp/"
    corporate_mcp_command: str = "corporate-rag-internal-mcp"
    corporate_mcp_args: tuple[str, ...] = ("--transport", "stdio")
    law_mcp_transport: str = "streamable_http"
    law_mcp_url: str = "http://127.0.0.1:18801/mcp/"
    law_mcp_command: str = "corporate-rag-law-mcp"
    law_mcp_args: tuple[str, ...] = ("--transport", "stdio")
    callback_ignore: tuple[str, ...] = (
        "RunnableLambda",
        "ChannelWrite",
        "Branch",
        "attach_output",
        "merge_message_runs",
        "compress_history",
    )
    callback_keep: tuple[str, ...] = ("tool", "agent", "llm")


def load_agent_settings() -> AgentSettings:
    return AgentSettings()


def load_app_settings() -> AppSettings:
    return AppSettings()


def load_auth_settings() -> AuthSettings:
    return AuthSettings()


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def load_neo4j_settings() -> Neo4jSettings:
    return Neo4jSettings()
