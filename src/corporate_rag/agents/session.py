from dataclasses import dataclass
from typing import Any, cast

import chainlit as cl
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool

from corporate_rag.agents.catalog import AgentModeId, default_chat_settings
from corporate_rag.corporate_agent.prompt import DEFAULT_AGENT_VERSION
from corporate_rag.settings import AgentSettings, load_agent_settings


@dataclass(slots=True)
class AgentSession:
    agent: Any
    mode: AgentModeId
    model_id: str
    tools: list[BaseTool]
    agent_version: str | None = None


async def build_agent_session(
    settings: AgentSettings,
    *,
    mode: AgentModeId,
    model_id: str,
    agent_version: str | None,
) -> AgentSession:
    if mode == "law":
        from corporate_rag.law_agent.agent import build_session as build_law_session

        return await build_law_session(settings, model_id=model_id)

    from corporate_rag.corporate_agent.agent import build_session as build_corporate_session

    return await build_corporate_session(
        settings,
        model_id=model_id,
        agent_version=agent_version,
    )


def current_mode() -> AgentModeId:
    mode = current_settings().get("Mode")
    return cast(AgentModeId, mode) if mode in {"corporate", "law"} else "corporate"


def remember_chat_settings(settings: dict[str, Any]) -> dict[str, Any]:
    merged = {**current_settings(), **settings}
    user_session_set("effective_chat_settings", merged)
    user_session_set("chat_settings", merged)
    return merged


def initialize_chat_settings() -> None:
    remember_chat_settings(default_chat_settings(load_agent_settings()))


async def ensure_agent_session() -> AgentSession:
    session = user_session_get("agent_session")
    if isinstance(session, AgentSession):
        return session
    return await set_agent_session()


async def set_agent_session(
    *,
    mode: str | None = None,
    model_id: str | None = None,
    agent_version: str | None = None,
) -> AgentSession:
    settings = load_agent_settings()
    chosen_mode: AgentModeId = (
        cast(AgentModeId, mode) if mode in {"corporate", "law"} else current_mode()
    )
    chosen_model_id = model_id or settings.default_model_id
    chosen_agent_version = agent_version or DEFAULT_AGENT_VERSION
    current_session = user_session_get("agent_session")

    if session_matches(
        current_session,
        mode=chosen_mode,
        model_id=chosen_model_id,
        agent_version=chosen_agent_version,
    ):
        return cast(AgentSession, current_session)

    session = await build_agent_session(
        settings,
        mode=chosen_mode,
        model_id=chosen_model_id,
        agent_version=chosen_agent_version,
    )
    user_session_set("agent_session", session)
    user_session_set("agent_session_mode", chosen_mode)
    user_session_set("agent_session_needs_history", True)
    return session


def agent_messages_for_turn(current_message_content: str) -> list[BaseMessage]:
    if user_session_get("agent_session_needs_history") is True:
        return messages_from_chat_context(cl.chat_context.get(), current_message_content)
    return [HumanMessage(content=current_message_content)]


def mark_history_synced() -> None:
    user_session_set("agent_session_needs_history", False)


def user_session_get(key: str) -> Any:
    return cl.user_session.get(key)  # type: ignore[no-untyped-call]


def user_session_set(key: str, value: Any) -> None:
    cl.user_session.set(key, value)  # type: ignore[no-untyped-call]


def current_settings() -> dict[str, Any]:
    effective = user_session_get("effective_chat_settings")
    if isinstance(effective, dict):
        return effective
    chainlit_settings = user_session_get("chat_settings")
    if isinstance(chainlit_settings, dict):
        return chainlit_settings
    return {}


def session_matches(
    session: Any,
    *,
    mode: AgentModeId,
    model_id: str,
    agent_version: str,
) -> bool:
    if not isinstance(session, AgentSession):
        return False
    if session.mode != mode or session.model_id != model_id:
        return False
    if mode == "law":
        return True
    return session.agent_version == agent_version


def messages_from_chat_context(
    chat_messages: list[Any],
    current_message_content: str,
) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for chat_message in chat_messages:
        content = str(getattr(chat_message, "content", "") or "").strip()
        if not content:
            continue
        message_type = getattr(chat_message, "type", None)
        if message_type == "user_message":
            messages.append(HumanMessage(content=content))
        elif message_type == "assistant_message":
            messages.append(AIMessage(content=content))
    if not messages or not _last_human_message_matches(messages, current_message_content):
        messages.append(HumanMessage(content=current_message_content))
    return messages


def _last_human_message_matches(messages: list[BaseMessage], content: str) -> bool:
    return (
        isinstance(messages[-1], HumanMessage)
        and str(messages[-1].content).strip() == content.strip()
    )
