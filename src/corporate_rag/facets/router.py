from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from corporate_rag.app.dependencies import graph_reader
from corporate_rag.facets.models import FacetResponse
from corporate_rag.facets.repository import resolve_facet
from corporate_rag.graph.interfaces import BaseGraphReader

router = APIRouter(
    prefix="/workflows",
    tags=["facets"],
    responses={503: {"description": "Graph reader is not configured."}},
)


@router.get(
    "/facet",
    response_model=FacetResponse,
    summary="List facet values for a workflow parameter",
    description=(
        "Returns available values and counts for select-like workflow filters, "
        "using the current form parameters as context."
    ),
)
async def facet(
    request: Request,
    reader: Annotated[BaseGraphReader, Depends(graph_reader)],
    workflow_id: str = Query(description="Workflow id that owns the parameter."),
    parameter_name: str = Query(description="Parameter name to facet."),
) -> dict[str, Any]:
    current_parameters = {
        key: value
        for key, value in request.query_params.items()
        if key not in {"workflow_id", "parameter_name"}
    }
    try:
        values = resolve_facet(
            reader,
            workflow_id=workflow_id,
            parameter_name=parameter_name,
            current_parameters=current_parameters,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"values": values}
