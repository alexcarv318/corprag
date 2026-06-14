from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver

from corporate_rag.agents.model import initialize_chat_model
from corporate_rag.agents.session import AgentSession
from corporate_rag.graph.interfaces import BaseGraphReader
from corporate_rag.graph.neo4j_client import build_law_graph_client
from corporate_rag.law_agent.prompt import system_prompt
from corporate_rag.law_agent.tools import build_langchain_tools
from corporate_rag.settings import AgentSettings, load_neo4j_settings

_graph: BaseGraphReader | None = None


async def build_session(
    settings: AgentSettings,
    *,
    model_id: str,
) -> AgentSession:
    graph = _graph_client()
    model = await initialize_chat_model(model_id, settings)
    tools = build_langchain_tools(graph)
    agent = create_deep_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt(),
        checkpointer=InMemorySaver(),
        name="lawrag",
    )
    return AgentSession(
        agent=agent,
        mode="law",
        model_id=model_id,
        tools=tools,
    )


def _graph_client() -> BaseGraphReader:
    global _graph
    if _graph is None:
        _graph = build_law_graph_client(load_neo4j_settings())
    return _graph
