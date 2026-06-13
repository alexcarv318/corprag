from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from corporate_rag.app.dependencies import graph_reader, typeahead_cache
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.typeahead.models import TypeaheadResponse
from corporate_rag.typeahead.repository import (
    TypeaheadCache,
    context_from_query,
    run_typeahead,
)

router = APIRouter(
    prefix="/workflows",
    tags=["typeahead"],
    responses={503: {"description": "Graph reader is not configured."}},
)


@router.get(
    "/typeahead",
    response_model=TypeaheadResponse,
    summary="Suggest graph values for workflow parameters",
    description=(
        "Returns lightweight autocomplete candidates for workflow form fields. "
        "Supported kinds include subjects, people, organizations, files, events, "
        "classes, and modules."
    ),
)
async def typeahead(
    reader: Annotated[BaseGraphReader, Depends(graph_reader)],
    cache: Annotated[TypeaheadCache, Depends(typeahead_cache)],
    kind: str = Query(description="Typeahead kind, for example `subject` or `person`."),
    q: str = Query(default="", description="Search text. Empty text returns browse results."),
    limit: int = Query(default=25, ge=1, le=10000, description="Maximum candidates to return."),
    subject_id: str | None = Query(default=None, description="Optional subject context filter."),
) -> dict[str, Any]:
    try:
        items, elapsed_ms, cache_hit = run_typeahead(
            reader,
            kind=kind,
            query_text=q.strip(),
            limit=limit,
            context=context_from_query({"subject_id": subject_id}),
            cache=cache,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "kind": kind,
        "query": q,
        "items": items,
        "elapsed_ms": elapsed_ms,
        "cache_hit": cache_hit,
    }
