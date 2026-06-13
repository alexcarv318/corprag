from pydantic import BaseModel, Field


class EvidenceRequest(BaseModel):
    value: str = Field(description="Cell value to explain with source chunks.")
    column: str = Field(description="Result column that produced the value.")
    files: list[str] = Field(default_factory=list, description="Candidate source files.")
    entity_id: str | None = Field(default=None, description="Optional graph entity id context.")
    context: str | None = Field(default=None, description="Optional ranking context text.")
    limit: int = Field(default=30, ge=1, le=200, description="Maximum chunks to return.")


class EvidenceChunkResponse(BaseModel):
    file: str
    chunk_id: str
    text: str
    snippet: str


class EvidenceResponse(BaseModel):
    value: str
    column: str
    highlight_terms: list[str]
    chunks: list[EvidenceChunkResponse]
