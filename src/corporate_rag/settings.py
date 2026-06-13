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


def load_app_settings() -> AppSettings:
    return AppSettings()


def load_neo4j_settings() -> Neo4jSettings:
    return Neo4jSettings()
