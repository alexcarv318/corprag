from typing import Annotated, NoReturn, cast

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from corporate_rag.auth.models import AuthUser
from corporate_rag.auth.repository import AuthRepository
from corporate_rag.auth.tokens import InvalidTokenError, verify_access_token
from corporate_rag.db.session import create_database_pool
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.settings import (
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    load_auth_settings,
    load_database_settings,
)
from corporate_rag.typeahead.repository import TypeaheadCache
from corporate_rag.workflows.engine import WorkflowEngine

AUTH_REALM = "corporate-rag"
_http_bearer = HTTPBearer(auto_error=False)


def app_settings(request: Request) -> AppSettings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, AppSettings):
        raise HTTPException(status_code=503, detail="app settings are not configured")
    return settings


def graph_reader(request: Request) -> BaseGraphReader:
    reader = getattr(request.app.state, "graph_reader", None)
    if not isinstance(reader, BaseGraphReader):
        raise HTTPException(status_code=503, detail="graph reader is not configured")
    return reader


def typeahead_cache(request: Request) -> TypeaheadCache:
    cache = getattr(request.app.state, "typeahead_cache", None)
    if not isinstance(cache, TypeaheadCache):
        cache = TypeaheadCache()
        request.app.state.typeahead_cache = cache
    return cache


def workflow_engine(request: Request) -> WorkflowEngine:
    engine = getattr(request.app.state, "workflow_engine", None)
    if not isinstance(engine, WorkflowEngine):
        raise HTTPException(status_code=503, detail="workflow engine is not configured")
    return engine


def auth_settings(request: Request) -> AuthSettings:
    settings = getattr(request.app.state, "auth_settings", None)
    if not isinstance(settings, AuthSettings):
        settings = load_auth_settings()
        request.app.state.auth_settings = settings
    return settings


def database_settings(request: Request) -> DatabaseSettings:
    settings = getattr(request.app.state, "database_settings", None)
    if not isinstance(settings, DatabaseSettings):
        settings = load_database_settings()
        request.app.state.database_settings = settings
    return settings


def auth_repository(
    request: Request,
    settings: Annotated[DatabaseSettings, Depends(database_settings)],
) -> AuthRepository:
    repository = getattr(request.app.state, "auth_repository", None)
    if repository is not None:
        return cast(AuthRepository, repository)

    pool = getattr(request.app.state, "database_pool", None)
    if pool is None:
        pool = create_database_pool(settings)
        request.app.state.database_pool = pool

    repository = AuthRepository(pool)
    request.app.state.auth_repository = repository
    return repository


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    repository: Annotated[AuthRepository, Depends(auth_repository)],
    settings: Annotated[AuthSettings, Depends(auth_settings)],
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise_unauthorized()

    try:
        payload = verify_access_token(credentials.credentials, settings.secret_key)
    except InvalidTokenError:
        raise_unauthorized()

    user = repository.get_user(str(payload["sub"]))
    if user is None:
        raise_unauthorized()

    return user


def raise_unauthorized() -> NoReturn:
    raise HTTPException(
        status_code=401,
        detail="invalid or expired token",
        headers={"WWW-Authenticate": f'Bearer realm="{AUTH_REALM}"'},
    )
