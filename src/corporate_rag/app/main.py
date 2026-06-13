from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from corporate_rag.app.health import router as health_router
from corporate_rag.documents.router import router as documents_router
from corporate_rag.evidence.router import router as evidence_router
from corporate_rag.facets.router import router as facets_router
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.graph.neo4j_client import build_corporate_graph_client
from corporate_rag.settings import AppSettings, load_app_settings, load_neo4j_settings
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

    app = FastAPI(
        title=resolved_settings.app_name,
        summary="Corporate graph workflow and document source API.",
        description=(
            "Clean backend API for the Corporate RAG product. The current surface "
            "covers graph workflows, workflow form helpers, evidence lookup, and "
            "document source retrieval. Legacy pilot routes are intentionally not "
            "exposed."
        ),
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
    )
    app.state.settings = resolved_settings
    app.state.workflow_engine = resolved_workflow_engine
    app.state.graph_reader = resolved_graph_reader

    if resolved_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    app.include_router(health_router)
    app.include_router(typeahead_router, prefix=resolved_settings.api_prefix)
    app.include_router(facets_router, prefix=resolved_settings.api_prefix)
    app.include_router(evidence_router, prefix=resolved_settings.api_prefix)
    app.include_router(workflows_router, prefix=resolved_settings.api_prefix)
    app.include_router(documents_router, prefix=resolved_settings.api_prefix)

    return app
