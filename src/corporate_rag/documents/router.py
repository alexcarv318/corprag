from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from corporate_rag.app.dependencies import graph_reader
from corporate_rag.documents.models import DocumentSourceResponse, DocumentTitlesResponse
from corporate_rag.documents.repository import fetch_document_source, fetch_document_titles
from corporate_rag.graph.interfaces import BaseGraphReader

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    responses={503: {"description": "Graph reader is not configured."}},
)


@router.get(
    "/source",
    response_model=DocumentSourceResponse,
    summary="Read document source text",
    description=(
        "Returns normalized document metadata and ordered source chunks for a "
        "file or item id referenced by workflow results."
    ),
)
async def document_source(
    reader: Annotated[BaseGraphReader, Depends(graph_reader)],
    file: str = Query(min_length=1, description="File name or graph item id."),
) -> dict[str, Any]:
    payload = fetch_document_source(reader, file)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"unknown document {file!r}")
    return payload


@router.get(
    "/titles",
    response_model=DocumentTitlesResponse,
    summary="Resolve document titles",
    description="Returns compact document metadata keyed by requested file names.",
)
async def document_titles(
    reader: Annotated[BaseGraphReader, Depends(graph_reader)],
    file: Annotated[
        list[str] | None,
        Query(description="One or more file names or item ids."),
    ] = None,
) -> dict[str, Any]:
    return {"titles": fetch_document_titles(reader, file or [])}
