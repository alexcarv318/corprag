from fastapi import HTTPException, Request

from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.settings import AppSettings
from corporate_rag.typeahead.repository import TypeaheadCache
from corporate_rag.workflows.engine import WorkflowEngine


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
