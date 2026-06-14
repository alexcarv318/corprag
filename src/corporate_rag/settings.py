from pydantic import Field
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


def load_app_settings() -> AppSettings:
    return AppSettings()


def load_auth_settings() -> AuthSettings:
    return AuthSettings()


def load_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


def load_neo4j_settings() -> Neo4jSettings:
    return Neo4jSettings()
