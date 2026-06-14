from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

from corporate_rag.agents.model import initialize_chat_model
from corporate_rag.agents.session import AgentSession
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.graph.neo4j_client import build_corporate_graph_client
from corporate_rag.internal_agent.prompt import DEFAULT_AGENT_VERSION, system_prompt
from corporate_rag.internal_agent.tools import build_langchain_tools
from corporate_rag.settings import AgentSettings, load_neo4j_settings
from corporate_rag.typeahead.repository import TypeaheadCache
from corporate_rag.workflows.catalog import CATALOG
from corporate_rag.workflows.engine import WorkflowEngine

_graph: BaseGraphReader | None = None
_engine: WorkflowEngine | None = None
_cache = TypeaheadCache()


async def build_session(
    settings: AgentSettings,
    *,
    model_id: str,
    agent_version: str | None,
) -> AgentSession:
    chosen_version = agent_version or DEFAULT_AGENT_VERSION
    graph, engine = _deps()
    model = await initialize_chat_model(model_id, settings)
    tools = build_langchain_tools(
        graph,
        engine,
        _cache,
        agent_version=chosen_version,
    )
    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt(chosen_version),
        checkpointer=InMemorySaver(),
        name="corprag",
    )
    return AgentSession(
        agent=agent,
        mode="internal",
        model_id=model_id,
        tools=tools,
        agent_version=chosen_version,
    )


def _deps() -> tuple[BaseGraphReader, WorkflowEngine]:
    global _graph, _engine
    if _graph is None or _engine is None:
        _graph = build_corporate_graph_client(load_neo4j_settings())
        _engine = WorkflowEngine(_graph, catalog=CATALOG)
    return _graph, _engine
