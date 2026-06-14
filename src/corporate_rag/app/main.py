import hashlib
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from chainlit.utils import mount_chainlit
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from corporate_rag.agents.api import router as agents_router
from corporate_rag.app.dependencies import current_user
from corporate_rag.app.health import router as health_router
from corporate_rag.auth.router import router as auth_router
from corporate_rag.documents.router import router as documents_router
from corporate_rag.evidence.router import router as evidence_router
from corporate_rag.facets.router import router as facets_router
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.graph.neo4j_client import build_corporate_graph_client
from corporate_rag.settings import (
    AppSettings,
    load_agent_settings,
    load_app_settings,
    load_auth_settings,
    load_database_settings,
    load_neo4j_settings,
)
from corporate_rag.typeahead.router import router as typeahead_router
from corporate_rag.workflows.catalog import CATALOG
from corporate_rag.workflows.engine import WorkflowEngine
from corporate_rag.workflows.router import router as workflows_router

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Service liveness and basic runtime metadata.",
    },
    {
        "name": "auth",
        "description": "Password user sign-up, sign-in, and bearer token identity checks.",
    },
    {
        "name": "workflows",
        "description": "Workflow catalog, definitions, disclaimer data, and workflow execution.",
    },
    {
        "name": "typeahead",
        "description": "Autocomplete candidates for graph-backed workflow parameters.",
    },
    {
        "name": "facets",
        "description": "Facet values and counts for workflow filters.",
    },
    {
        "name": "evidence",
        "description": "Source chunks that explain values returned by workflow tables.",
    },
    {
        "name": "documents",
        "description": "Document source text and compact document metadata.",
    },
    {
        "name": "agents",
        "description": "Native React agent configuration and Chainlit protocol handoff.",
    },
]


def create_app(
    settings: AppSettings | None = None,
    workflow_engine: WorkflowEngine | None = None,
    graph_reader: BaseGraphReader | None = None,
    configure_workflows: bool = True,
) -> FastAPI:
    resolved_settings = settings or load_app_settings()
    resolved_workflow_engine = workflow_engine
    resolved_graph_reader = graph_reader
    if resolved_workflow_engine is None and configure_workflows:
        graph_client = build_corporate_graph_client(load_neo4j_settings())
        resolved_workflow_engine = WorkflowEngine(graph_client, catalog=CATALOG)
        resolved_graph_reader = graph_client
    elif resolved_workflow_engine is not None and resolved_graph_reader is None:
        resolved_graph_reader = resolved_workflow_engine.client

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            pool = getattr(application.state, "database_pool", None)
            if pool is not None:
                pool.close()

    app = FastAPI(
        title=resolved_settings.app_name,
        summary="Corporate graph workflow and document source API.",
        description=(
            "Clean backend API for the Corporate RAG product. The current surface "
            "covers graph workflows, workflow form helpers, evidence lookup, and "
            "document source retrieval."
        ),
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.workflow_engine = resolved_workflow_engine
    app.state.graph_reader = resolved_graph_reader
    app.state.agent_settings = load_agent_settings()
    app.state.auth_settings = load_auth_settings()
    app.state.database_settings = load_database_settings()

    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    app.include_router(auth_router, prefix=resolved_settings.api_prefix)
    protected_dependencies = [Depends(current_user)]
    app.include_router(health_router, dependencies=protected_dependencies)
    app.include_router(
        typeahead_router,
        prefix=resolved_settings.api_prefix,
        dependencies=protected_dependencies,
    )
    app.include_router(
        facets_router,
        prefix=resolved_settings.api_prefix,
        dependencies=protected_dependencies,
    )
    app.include_router(
        evidence_router,
        prefix=resolved_settings.api_prefix,
        dependencies=protected_dependencies,
    )
    app.include_router(
        workflows_router,
        prefix=resolved_settings.api_prefix,
        dependencies=protected_dependencies,
    )
    app.include_router(
        documents_router,
        prefix=resolved_settings.api_prefix,
        dependencies=protected_dependencies,
    )
    app.include_router(
        agents_router,
        prefix=resolved_settings.api_prefix,
        dependencies=protected_dependencies,
    )

    _mount_chainlit_runtime(app)

    return app


def _mount_chainlit_runtime(app: FastAPI) -> None:
    agent_config = load_agent_settings()
    auth_config = load_auth_settings()
    chainlit_secret = hashlib.sha256(auth_config.secret_key.encode("utf-8")).hexdigest()
    os.environ.setdefault("CHAINLIT_AUTH_SECRET", chainlit_secret)
    # Chainlit persistence is configured explicitly in agents/chainlit_app.py
    # against CORPORATE_RAG_DATABASE_URL.
    os.environ.pop("DATABASE_URL", None)
    target = Path(__file__).resolve().parents[1] / "agents" / "chainlit_app.py"
    mount_chainlit(app=app, target=str(target), path=agent_config.chainlit_mount_path)
