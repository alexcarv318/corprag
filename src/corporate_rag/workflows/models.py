from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

ParameterKind = Literal["string", "number", "date", "select", "boolean"]


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    label: str
    kind: ParameterKind = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    options: tuple[str, ...] | None = None
    placeholder: str | None = None
    multiple: bool = False
    gated_default: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "kind": self.kind,
            "required": self.required,
            "default": self.default,
            "options": list(self.options) if self.options is not None else None,
            "placeholder": self.placeholder,
            "multiple": self.multiple,
            "gated_default": self.gated_default,
        }


@dataclass(frozen=True, slots=True)
class Workflow:
    workflow_id: str
    title: str
    category: str
    description: str
    cypher: str
    parameters: tuple[Parameter, ...] = field(default_factory=tuple)
    output_columns: tuple[str, ...] = field(default_factory=tuple)
    notes: str | None = None
    use_cases: tuple[str, ...] = field(default_factory=tuple)
    dev_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "cypher": self.cypher,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "output_columns": list(self.output_columns),
            "notes": self.notes,
            "use_cases": list(self.use_cases),
            "dev_only": self.dev_only,
        }


@dataclass(frozen=True, slots=True)
class WorkflowResultTable:
    table_id: str
    title: str
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "table_id": self.table_id,
            "title": self.title,
            "rows": self.rows,
            "columns": self.columns,
            "row_count": self.row_count,
        }


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    workflow_id: str
    parameters: dict[str, Any]
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    elapsed_ms: float
    cypher: str
    tables: tuple[WorkflowResultTable, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        tables = [table.to_dict() for table in self.tables]
        if not tables:
            tables = [
                WorkflowResultTable(
                    table_id=self.workflow_id,
                    title="Results",
                    rows=self.rows,
                    columns=self.columns,
                    row_count=self.row_count,
                ).to_dict()
            ]
        return {
            "workflow_id": self.workflow_id,
            "parameters": self.parameters,
            "rows": self.rows,
            "columns": self.columns,
            "row_count": self.row_count,
            "elapsed_ms": self.elapsed_ms,
            "cypher": self.cypher,
            "tables": tables,
        }


def include_cancelled_parameter() -> Parameter:
    return Parameter(
        name="include_cancelled",
        label="Show inactive",
        kind="boolean",
        default=False,
        description=(
            "Also show items that are no longer in force: cancelled, revoked, "
            "expired, or superseded."
        ),
    )


class WorkflowRunRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)


class WorkflowParameterResponse(BaseModel):
    name: str
    label: str
    description: str
    kind: str
    required: bool
    default: Any = None
    options: list[str] | None = None
    placeholder: str | None = None
    multiple: bool
    gated_default: bool


class WorkflowResponse(BaseModel):
    workflow_id: str
    title: str
    category: str
    description: str
    cypher: str
    parameters: list[WorkflowParameterResponse]
    output_columns: list[str]
    notes: str | None = None
    use_cases: list[str]
    dev_only: bool


class WorkflowCatalogResponse(BaseModel):
    categories: list[str]
    workflows: list[WorkflowResponse]


class WorkflowResultTableResponse(BaseModel):
    table_id: str
    title: str
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int


class WorkflowResultResponse(BaseModel):
    workflow_id: str
    parameters: dict[str, Any]
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    elapsed_ms: float
    cypher: str
    tables: list[WorkflowResultTableResponse]


class WorkflowDisclaimerResponse(BaseModel):
    document_count: int
