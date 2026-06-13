from typing import Annotated, Any

from fastapi import APIRouter, Depends

from corporate_rag.app.dependencies import graph_reader
from corporate_rag.evidence.models import EvidenceRequest, EvidenceResponse
from corporate_rag.evidence.repository import resolve_value_evidence
from corporate_rag.graph.interfaces import BaseGraphReader

router = APIRouter(
    prefix="/workflows",
    tags=["evidence"],
    responses={503: {"description": "Graph reader is not configured."}},
)


@router.post(
    "/evidence",
    response_model=EvidenceResponse,
    summary="Find source chunks for a workflow result value",
    description=(
        "Looks up source document chunks that can support or explain a value "
        "shown in a workflow result table."
    ),
)
async def evidence(
    payload: EvidenceRequest,
    reader: Annotated[BaseGraphReader, Depends(graph_reader)],
) -> dict[str, Any]:
    return resolve_value_evidence(
        reader,
        value=payload.value,
        column=payload.column,
        files=payload.files,
        entity_id=payload.entity_id,
        context=payload.context,
        limit=payload.limit,
    )
