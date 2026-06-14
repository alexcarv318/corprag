from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model

from corporate_rag.agents.tool_output import normalize_tool_outputs
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.internal_agent import repository
from corporate_rag.internal_agent.prompt import DEFAULT_AGENT_VERSION
from corporate_rag.typeahead.repository import TypeaheadCache, run_typeahead
from corporate_rag.workflows.engine import WorkflowEngine
from corporate_rag.workflows.models import Parameter, Workflow, WorkflowResult, WorkflowResultTable

ResolveEntityKind = Literal[
    "subject",
    "organization",
    "person",
    "phase",
    "event",
    "work",
    "file",
]

WORKFLOWS_MODE_TOOL_WHITELIST = frozenset(
    {
        "resolve_entity",
        "find_subject",
        "find_subject_identifiers",
        "find_subject_board_history",
        "find_organization",
        "find_organization_identifiers",
        "find_organization_offices",
        "find_person",
        "find_person_roles",
        "find_documents",
        "find_by_identifier",
        "get_work",
        "read_chunks",
        "entity_mentions",
        "capital_shareholdings",
        "powers_of_attorney",
        "events_timeline",
    }
)


@dataclass(frozen=True, slots=True)
class WorkflowToolView:
    workflow_id: str
    table_id: str | None = None
    default_params: dict[str, Any] = field(default_factory=dict)


WORKFLOW_TOOL_VIEWS: dict[str, WorkflowToolView] = {
    "find_subject": WorkflowToolView("find.subject", "subject_phases"),
    "find_subject_identifiers": WorkflowToolView("find.subject", "subject_identifiers"),
    "find_subject_board_history": WorkflowToolView("find.subject", "subject_board_history"),
    "find_organization": WorkflowToolView("find.organization", "organization"),
    "find_organization_identifiers": WorkflowToolView(
        "find.organization",
        "organization_identifiers",
    ),
    "find_organization_offices": WorkflowToolView("find.organization", "organization_offices"),
    "find_person": WorkflowToolView("find.person", "person"),
    "find_person_roles": WorkflowToolView("find.person", "person_roles_and_affiliations"),
    "find_documents": WorkflowToolView("documents.search"),
    "capital_shareholdings": WorkflowToolView("capital.shareholdings"),
    "powers_of_attorney": WorkflowToolView("governance.poa.register"),
    "events_timeline": WorkflowToolView("events.timeline"),
}


def tool_whitelist(agent_version: str | None = None) -> frozenset[str] | None:
    if (agent_version or DEFAULT_AGENT_VERSION) == "v2.workflows":
        return WORKFLOWS_MODE_TOOL_WHITELIST
    return None


def resolve_entity(
    graph: BaseGraphReader,
    cache: TypeaheadCache,
    *,
    kind: str,
    q: str = "",
    limit: int = 10,
    context_subject_id: str | None = None,
) -> list[dict[str, Any]]:
    context = {"subject_id": context_subject_id} if context_subject_id else None
    rows, _, _ = run_typeahead(
        graph,
        kind=kind,
        query_text=q,
        limit=limit,
        context=context,
        cache=cache,
    )
    ranked = sorted(rows, key=lambda row: _ranking_key(row, q), reverse=True)
    return ranked[:limit]


def run_workflow_tool(
    engine: WorkflowEngine,
    view: WorkflowToolView,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    merged = {**view.default_params, **parameters}
    result = engine.run(view.workflow_id, merged)
    table = _select_table(result, view.table_id)
    return {
        "workflow_id": result.workflow_id,
        "parameters": result.parameters,
        "columns": table.columns,
        "rows": table.rows,
        "row_count": table.row_count,
        "elapsed_ms": result.elapsed_ms,
    }


def build_langchain_tools(
    graph: BaseGraphReader,
    engine: WorkflowEngine,
    cache: TypeaheadCache,
    *,
    agent_version: str | None,
) -> list[BaseTool]:
    async def resolve_entity_tool(
        kind: str,
        q: str = "",
        limit: int = 10,
        context_subject_id: str | None = None,
    ) -> list[dict[str, Any]]:
        return resolve_entity(
            graph,
            cache,
            kind=kind,
            q=q,
            limit=limit,
            context_subject_id=context_subject_id,
        )

    async def entity_mentions_tool(
        entity_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return repository.entity_mentions(
            graph,
            entity_id=entity_id,
            limit=limit,
        )

    async def find_by_identifier_tool(
        value: str,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        return repository.find_by_identifier(
            graph,
            value=value,
            kind=kind,
        )

    async def get_work_tool(work_id: str) -> dict[str, Any] | None:
        return repository.get_work(graph, work_id=work_id)

    async def read_chunks_tool(
        file: str | None = None,
        chunk_ids: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return repository.read_chunks(
            graph,
            file=file,
            chunk_ids=chunk_ids or [],
            limit=limit,
        )

    tools: list[BaseTool] = [
        StructuredTool.from_function(
            coroutine=resolve_entity_tool,
            name="resolve_entity",
            description=(
                "Resolve a named entity to canonical ids. "
                "Kinds: subject, organization, person, phase, event, work, file."
            ),
        ),
        StructuredTool.from_function(
            coroutine=entity_mentions_tool,
            name="entity_mentions",
            description="Return quote-bearing chunks that ground one entity.",
        ),
        StructuredTool.from_function(
            coroutine=find_by_identifier_tool,
            name="find_by_identifier",
            description="Reverse lookup owners by registration or identifier value.",
        ),
        StructuredTool.from_function(
            coroutine=get_work_tool,
            name="get_work",
            description="Read work metadata and file linkage for one work id.",
        ),
        StructuredTool.from_function(
            coroutine=read_chunks_tool,
            name="read_chunks",
            description="Read document chunks by inbox file name or chunk ids.",
        ),
    ]
    for tool_name, view in WORKFLOW_TOOL_VIEWS.items():
        workflow = engine.get_workflow(view.workflow_id)
        description = workflow.description.strip()
        if workflow.use_cases:
            description = f"{description} Use cases: {' | '.join(workflow.use_cases)}"

        tools.append(
            StructuredTool.from_function(
                coroutine=_workflow_runner(engine, view),
                args_schema=_workflow_args_schema(workflow, tool_name),
                name=tool_name,
                description=description,
            )
        )

    whitelist = tool_whitelist(agent_version)
    if whitelist is not None:
        tools = [tool for tool in tools if tool.name in whitelist]
    return normalize_tool_outputs(tools)


def _workflow_runner(
    engine: WorkflowEngine,
    view: WorkflowToolView,
) -> Any:
    async def run(**parameters: Any) -> dict[str, Any]:
        return run_workflow_tool(engine, view, parameters)

    return run


def _workflow_args_schema(workflow: Workflow, tool_name: str) -> type[BaseModel]:
    fields: dict[str, Any] = {}
    for parameter in workflow.parameters:
        annotation = _parameter_annotation(parameter)
        default = ... if parameter.required else parameter.default
        fields[parameter.name] = (
            annotation,
            Field(
                default,
                description=parameter.description or parameter.label,
            ),
        )
    return create_model(f"{_schema_name(tool_name)}Args", **fields)


def _parameter_annotation(parameter: Parameter) -> type[Any]:
    if parameter.multiple:
        return list[str]
    if parameter.kind == "boolean":
        return bool
    if parameter.kind == "number":
        return float
    return str


def _schema_name(tool_name: str) -> str:
    return "".join(part.capitalize() for part in tool_name.split("_"))


def _select_table(result: WorkflowResult, table_id: str | None) -> WorkflowResultTable:
    if table_id and result.tables:
        for table in result.tables:
            if table.table_id == table_id:
                return table
    if result.tables:
        return result.tables[0]
    return WorkflowResultTable(
        table_id=result.workflow_id,
        title="Results",
        rows=result.rows,
        columns=result.columns,
        row_count=result.row_count,
    )


def _ranking_key(row: dict[str, Any], query_text: str) -> tuple[float, float, int]:
    if not query_text:
        return (
            float(row.get("score") or 0.0),
            float(row.get("edge_count") or 0),
            0,
        )
    label = str(row.get("label") or "")
    query_lower = query_text.strip().lower()
    values = [label]
    aliases = row.get("aliases") or []
    if isinstance(aliases, list):
        values.extend(str(alias) for alias in aliases if alias)
    elif aliases:
        values.append(str(aliases))
    lowered_values = [value.lower() for value in values if value]
    similarity = max(
        SequenceMatcher(None, query_lower, value).ratio() for value in lowered_values
    )
    exact_bonus = 0
    for value in lowered_values:
        if value == query_lower:
            exact_bonus = max(exact_bonus, 3)
        elif value.startswith(query_lower):
            exact_bonus = max(exact_bonus, 2)
        elif query_lower in value:
            exact_bonus = max(exact_bonus, 1)
    return (
        float(row.get("score") or 0.0) + similarity + exact_bonus,
        similarity,
        int(row.get("edge_count") or 0),
    )
