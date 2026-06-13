from typing import Any

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str | None = None
    sequence_index: int | None = None
    structural_role: str | None = None
    structural_path: str | None = None
    page_first: int | None = None
    page_last: int | None = None
    text: str | None = None


class DocumentSourceResponse(BaseModel):
    work_id: str | None = None
    title: str | None = None
    doc_type: str | None = None
    summary: str | None = None
    work_lifecycle_status: str | None = None
    expression_lifecycle_status: str | None = None
    item_lifecycle_status: str | None = None
    item_id: str | None = None
    file: str | None = None
    chunks: list[DocumentChunk] = Field(default_factory=list)


class DocumentTitlesResponse(BaseModel):
    titles: dict[str, dict[str, Any]]
