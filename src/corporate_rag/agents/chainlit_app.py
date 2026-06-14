import json
from typing import Any

import chainlit as cl
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict
from langchain_core.runnables import RunnableConfig

from corporate_rag.agents.catalog import AgentModeId, starters_for_mode
from corporate_rag.agents.data_layer import ProductUserSQLAlchemyDataLayer
from corporate_rag.agents.handoff import (
    InvalidHandoffTokenError,
    handoff_token_from_cookie,
    verify_handoff_token,
)
from corporate_rag.agents.session import (
    agent_messages_for_turn,
    current_mode,
    ensure_agent_session,
    initialize_chat_settings,
    mark_history_synced,
    remember_chat_settings,
    set_agent_session,
)
from corporate_rag.agents.tool_output import (
    ToolCallEvent,
    reset_tool_event_observer,
    set_tool_event_observer,
)
from corporate_rag.settings import (
    load_agent_settings,
    load_auth_settings,
    load_database_settings,
)


def _chainlit_conninfo() -> str:
    database_url = load_database_settings().database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


@cl.data_layer
def get_data_layer() -> SQLAlchemyDataLayer:
    return ProductUserSQLAlchemyDataLayer(conninfo=_chainlit_conninfo())


@cl.header_auth_callback
async def header_auth_callback(headers: Any) -> cl.User | None:
    settings = load_agent_settings()
    token = handoff_token_from_cookie(
        str(headers.get("cookie") or ""),
        settings.handoff_cookie_name,
    )
    if token is None:
        return None
    try:
        user = verify_handoff_token(token, auth_settings=load_auth_settings())
    except InvalidHandoffTokenError:
        return None
    return cl.User(
        identifier=user["id"],
        display_name=user["username"],
        metadata={"provider": "corporate-rag", "username": user["username"]},
    )


@cl.set_starters
async def set_starters(
    current_user: cl.User | None,
    language: str | None = None,
) -> list[cl.Starter]:
    del current_user, language
    return [
        cl.Starter(label=starter.label, message=starter.message)
        for starter in starters_for_mode(current_mode())
    ]


@cl.author_rename
async def rename_author(original_author: str) -> str:
    if original_author == "Assistant":
        return "Lawrag" if current_mode() == "law" else "Corprag"
    return original_author


@cl.on_chat_start
async def on_chat_start() -> None:
    initialize_chat_settings()


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict) -> None:
    del thread
    initialize_chat_settings()


@cl.on_settings_update
async def on_settings_update(settings: dict[str, Any]) -> None:
    merged = remember_chat_settings(settings)
    if cl.user_session.get("agent_session") is not None:  # type: ignore[no-untyped-call]
        await set_agent_session(
            mode=merged.get("Mode") if isinstance(merged.get("Mode"), str) else None,
            model_id=merged.get("Model") if isinstance(merged.get("Model"), str) else None,
            agent_version=(
                merged.get("AgentVersion")
                if isinstance(merged.get("AgentVersion"), str)
                else None
            ),
        )


@cl.on_message
async def on_message(message: cl.Message) -> None:
    session = await ensure_agent_session()
    mode = current_mode()
    config = RunnableConfig(configurable={"thread_id": cl.context.session.thread_id})

    final_message = cl.Message(content="", author="Lawrag" if mode == "law" else "Corprag")
    raw_buffer: list[str] = []
    observer_token = set_tool_event_observer(_send_tool_event)
    try:
        async for token, metadata in session.agent.astream(
            {"messages": agent_messages_for_turn(message.content)},
            stream_mode="messages",
            config=config,
        ):
            text = _token_text(token)
            if text and _should_stream_token(metadata):
                raw_buffer.append(text)
                await final_message.stream_token(text)
    finally:
        reset_tool_event_observer(observer_token)

    await _finalize_message(final_message, "".join(raw_buffer), mode=mode)
    mark_history_synced()


def _token_text(token: Any) -> str:
    content = getattr(token, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(item.get("text") or "") for item in content if isinstance(item, dict))
    return ""


def _should_stream_token(metadata: Any) -> bool:
    return isinstance(metadata, dict) and metadata.get("langgraph_node") in {"agent", "model"}


async def _finalize_message(
    final_message: cl.Message,
    raw_text: str,
    *,
    mode: AgentModeId,
) -> None:
    if mode == "law":
        from corporate_rag.law_agent.citations import finalize_message

        await finalize_message(final_message, raw_text)
        return

    from corporate_rag.internal_agent.citations import finalize_message

    await finalize_message(final_message, raw_text)


async def _send_tool_event(event: ToolCallEvent) -> None:
    step = cl.Step(name=event.tool_name, type="tool", show_input="json")
    step.input = event.arguments
    step.output = _format_tool_event(event)
    step.is_error = event.phase == "error"
    await step.send()  # type: ignore[no-untyped-call]


def _format_tool_event(event: ToolCallEvent) -> str:
    if event.phase == "start":
        return "\n".join(
            (
                "Calling tool.",
                f"Arguments: {_json_preview(event.arguments)}",
            )
        )
    if event.phase == "success":
        return "\n".join(
            (
                "Tool completed.",
                f"Result preview: {event.preview or 'No result.'}",
            )
        )
    return "\n".join(
        (
            "Tool failed.",
            f"Error preview: {event.preview or 'No error details.'}",
        )
    )


def _json_preview(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=True, sort_keys=True)
