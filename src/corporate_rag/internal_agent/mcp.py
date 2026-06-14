from mcp.server.fastmcp import FastMCP

from corporate_rag.internal_agent import repository
from corporate_rag.internal_agent.agent import _deps
from corporate_rag.internal_agent.tools import (
    WORKFLOW_TOOL_VIEWS,
    WorkflowToolView,
    resolve_entity,
    run_workflow_tool,
)
from corporate_rag.typeahead.repository import TypeaheadCache

_cache = TypeaheadCache()


def build_server(*, host: str = "127.0.0.1", port: int = 18800) -> FastMCP:
    graph, engine = _deps()
    server = FastMCP(
        name="corporate-rag-internal-agent",
        host=host,
        port=port,
        json_response=True,
        stateless_http=True,
    )

    @server.tool(name="resolve_entity")
    def resolve_entity_tool(
        kind: str,
        q: str = "",
        limit: int = 10,
        context_subject_id: str | None = None,
    ) -> list[dict[str, object]]:
        return resolve_entity(
            graph,
            _cache,
            kind=kind,
            q=q,
            limit=limit,
            context_subject_id=context_subject_id,
        )

    @server.tool(name="entity_mentions")
    def entity_mentions_tool(entity_id: str, limit: int = 20) -> list[dict[str, object]]:
        return repository.entity_mentions(graph, entity_id=entity_id, limit=limit)

    @server.tool(name="find_by_identifier")
    def find_by_identifier_tool(value: str, kind: str | None = None) -> list[dict[str, object]]:
        return repository.find_by_identifier(graph, value=value, kind=kind)

    @server.tool(name="get_work")
    def get_work_tool(work_id: str) -> dict[str, object] | None:
        return repository.get_work(graph, work_id=work_id)

    @server.tool(name="read_chunks")
    def read_chunks_tool(
        file: str | None = None,
        chunk_ids: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        return repository.read_chunks(
            graph,
            file=file,
            chunk_ids=chunk_ids or [],
            limit=limit,
        )

    for tool_name, view in WORKFLOW_TOOL_VIEWS.items():
        workflow = engine.get_workflow(view.workflow_id)
        description = workflow.description.strip()

        def register(
            name: str = tool_name,
            selected_view: WorkflowToolView = view,
            tool_description: str = description,
        ) -> None:
            @server.tool(name=name, description=tool_description)
            def workflow_tool(**kwargs: object) -> dict[str, object]:
                return run_workflow_tool(engine, selected_view, dict(kwargs))

        register()

    return server


def main(
    host: str = "127.0.0.1",
    port: int = 18800,
    transport: str = "streamable-http",
) -> None:
    server = build_server(host=host, port=port)
    if transport == "stdio":
        server.run(transport="stdio")
        return
    server.run(transport="streamable-http")
