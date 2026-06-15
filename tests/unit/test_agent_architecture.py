import asyncio
from typing import Any
from unittest.mock import MagicMock

from langchain_core.tools import BaseTool, StructuredTool

from corporate_rag.agents.model import AgentModelConfigurationError
from corporate_rag.agents.session import build_agent_session
from corporate_rag.agents.tool_output import (
    ToolCallEvent,
    normalize_tool_outputs,
    reset_tool_event_observer,
    set_tool_event_observer,
)
from corporate_rag.corporate_agent.tools import (
    WORKFLOW_TOOL_VIEWS,
    build_langchain_tools,
    run_workflow_tool,
    tool_whitelist,
)
from corporate_rag.settings import AgentSettings
from corporate_rag.typeahead.repository import TypeaheadCache
from corporate_rag.workflows.catalog import CATALOG
from corporate_rag.workflows.engine import WorkflowEngine
from tests.unit.test_workflow_engine import SequencedGraphReader


class DummyTool(BaseTool):
    name: str
    description: str = "Test tool."

    def _run(self, *args: Any, **kwargs: Any) -> str:
        del args, kwargs
        return "ok"

    async def _arun(self, *args: Any, **kwargs: Any) -> str:
        del args, kwargs
        return "ok"


def test_corporate_agent_versions_own_tool_policy() -> None:
    assert tool_whitelist("v2.default") is None
    workflows_whitelist = tool_whitelist("v2.workflows")
    assert workflows_whitelist is not None
    assert "resolve_entity" in workflows_whitelist
    assert "find_subject" in workflows_whitelist
    assert "search_documents_fulltext" in workflows_whitelist
    assert "search_chunks_fulltext" in workflows_whitelist
    assert "corpus_overview" in workflows_whitelist
    assert "list_business_subjects" in workflows_whitelist
    assert "outside_tool" not in workflows_whitelist


def test_normalized_tool_errors_are_returned_to_agent() -> None:
    async def failing_tool(subject_id: str | None = None) -> dict[str, str]:
        if subject_id is None:
            raise ValueError("Workflow 'find.subject' requires parameter 'subject_id'.")
        return {"subject_id": subject_id}

    tool = StructuredTool.from_function(
        coroutine=failing_tool,
        name="find_subject",
        description="Find one subject.",
    )
    wrapped = normalize_tool_outputs([tool])[0]
    result = asyncio.run(wrapped.ainvoke({}))
    assert result["error"] == "ValueError"


def test_normalized_tools_emit_compact_tool_events() -> None:
    async def echo_tool(value: str) -> dict[str, str]:
        return {"value": value}

    async def run_tool() -> list[ToolCallEvent]:
        events: list[ToolCallEvent] = []

        async def observe(event: ToolCallEvent) -> None:
            events.append(event)

        token = set_tool_event_observer(observe)
        try:
            tool = StructuredTool.from_function(
                coroutine=echo_tool,
                name="echo",
                description="Echo a value.",
            )
            wrapped = normalize_tool_outputs([tool])[0]
            await wrapped.ainvoke({"value": "abc"})
            return events
        finally:
            reset_tool_event_observer(token)

    events = asyncio.run(run_tool())

    assert [event.phase for event in events] == ["start", "success"]
    assert [event.tool_name for event in events] == ["echo", "echo"]
    assert events[0].arguments == {"value": "abc"}
    assert events[1].preview == "{'value': 'abc'}"


def test_generated_workflow_tools_accept_catalog_parameters_directly() -> None:
    graph = SequencedGraphReader(
        [
            [{"subject_id": "subject-aeh", "subject": "AEH"}],
            [{"identifier": "CHE-123", "kind": "RegistrationIdentifier"}],
            [{"person": "Jane", "role": "Director"}],
        ]
    )
    engine = WorkflowEngine(graph, catalog=CATALOG)
    tools = build_langchain_tools(
        graph,
        engine,
        TypeaheadCache(),
        agent_version="v2.default",
    )
    board_tool = next(tool for tool in tools if tool.name == "find_subject_board_history")

    assert "subject_id" in board_tool.args
    assert "kwargs" not in board_tool.args
    assert "selected_view" not in board_tool.args

    result = asyncio.run(board_tool.ainvoke({"subject_id": "subject-aeh"}))

    assert result["parameters"] == {"subject_id": "subject-aeh"}
    assert result["columns"]


def test_history_workflow_tools_default_to_full_agent_context() -> None:
    graph = SequencedGraphReader([[{"event": "Capital contribution"}]])
    engine = WorkflowEngine(graph, catalog=CATALOG)

    result = run_workflow_tool(
        engine,
        WORKFLOW_TOOL_VIEWS["capital_shareholdings"],
        {"subject_id": "subject-aeh", "include_cancelled": None},
    )

    assert result["parameters"]["subject_id"] == "subject-aeh"
    assert result["parameters"]["include_cancelled"] is True
    assert result["parameters"]["limit"] == 100


def test_agent_exposes_fulltext_and_corpus_tools() -> None:
    graph = SequencedGraphReader([])
    engine = WorkflowEngine(graph, catalog=CATALOG)
    tools = build_langchain_tools(
        graph,
        engine,
        TypeaheadCache(),
        agent_version="v2.workflows",
    )
    tool_names = {tool.name for tool in tools}

    assert "search_documents_fulltext" in tool_names
    assert "search_chunks_fulltext" in tool_names
    assert "corpus_overview" in tool_names
    assert "list_business_subjects" in tool_names


def test_openai_model_initialization_passes_explicit_api_key(monkeypatch: Any) -> None:
    from corporate_rag.agents import model

    captured: dict[str, Any] = {}

    def fake_init_chat_model(model_id: str, **kwargs: Any) -> dict[str, Any]:
        captured["model_id"] = model_id
        captured["kwargs"] = kwargs
        return {"model": model_id}

    monkeypatch.setattr(model, "init_chat_model", fake_init_chat_model)
    initialized: Any = asyncio.run(
        model.initialize_chat_model(
            "openai:gpt-4.1",
            AgentSettings(openai_api_key="test-key"),
        )
    )
    assert initialized == {"model": "openai:gpt-4.1"}
    assert captured["kwargs"] == {"api_key": "test-key"}


def test_openai_model_initialization_requires_api_key() -> None:
    from corporate_rag.agents import model

    try:
        asyncio.run(
            model.initialize_chat_model(
                "openai:gpt-4.1",
                AgentSettings(openai_api_key=None),
            )
        )
    except AgentModelConfigurationError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected AgentModelConfigurationError")


def test_corporate_session_builds_deep_agent(monkeypatch: Any) -> None:
    from corporate_rag.corporate_agent import agent as corporate_agent_module

    captured: dict[str, Any] = {}

    def fake_create_deep_agent(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"agent": "corporate"}

    async def fake_initialize_chat_model(model_id: str, settings: AgentSettings) -> dict[str, str]:
        del settings
        return {"model": model_id}

    monkeypatch.setattr(
        corporate_agent_module,
        "initialize_chat_model",
        fake_initialize_chat_model,
    )
    monkeypatch.setattr(corporate_agent_module, "create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr(
        corporate_agent_module,
        "build_langchain_tools",
        lambda *args, **kwargs: [DummyTool(name="find_subject")],
    )
    monkeypatch.setattr(corporate_agent_module, "_deps", lambda: (MagicMock(), MagicMock()))

    session = asyncio.run(
        build_agent_session(
            AgentSettings(default_model_id="openai:gpt-4.1"),
            mode="corporate",
            model_id="openai:gpt-4.1",
            agent_version="v2.workflows",
        )
    )
    assert session.mode == "corporate"
    assert captured["name"] == "corprag"


def test_law_session_builds_deep_agent(monkeypatch: Any) -> None:
    from corporate_rag.law_agent import agent as law_agent_module

    captured: dict[str, Any] = {}

    def fake_create_deep_agent(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"agent": "law"}

    async def fake_initialize_chat_model(model_id: str, settings: AgentSettings) -> dict[str, str]:
        del settings
        return {"model": model_id}

    monkeypatch.setattr(law_agent_module, "initialize_chat_model", fake_initialize_chat_model)
    monkeypatch.setattr(law_agent_module, "create_deep_agent", fake_create_deep_agent)
    monkeypatch.setattr(
        law_agent_module,
        "build_langchain_tools",
        lambda graph: [DummyTool(name="get_article")],
    )
    monkeypatch.setattr(law_agent_module, "_graph_client", lambda: MagicMock())

    session = asyncio.run(
        build_agent_session(
            AgentSettings(default_model_id="openai:gpt-4.1"),
            mode="law",
            model_id="openai:gpt-4.1",
            agent_version=None,
        )
    )
    assert session.mode == "law"
    assert captured["name"] == "lawrag"
