import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from corporate_rag.settings import load_database_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _sqlalchemy_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url", "")
    expanded_url = os.path.expandvars(configured_url)
    database_url = (
        expanded_url
        if expanded_url and "$" not in expanded_url
        else load_database_settings().database_url
    )
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_sqlalchemy_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _sqlalchemy_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
