from collections.abc import Awaitable, Callable, Sequence
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, cast

from langchain_core.tools import BaseTool, StructuredTool
from neo4j.time import Date as Neo4jDate
from neo4j.time import DateTime as Neo4jDateTime

MAX_TOOL_PREVIEW_LENGTH = 900

type ToolEventPhase = Literal["start", "success", "error"]
type ToolEventObserver = Callable[["ToolCallEvent"], Awaitable[None]]

_tool_event_observer: ContextVar[ToolEventObserver | None] = ContextVar(
    "tool_event_observer",
    default=None,
)


@dataclass(frozen=True, slots=True)
class ToolCallEvent:
    phase: ToolEventPhase
    tool_name: str
    arguments: dict[str, Any]
    preview: str | None = None


def normalize_tool_outputs(tools: Sequence[BaseTool]) -> list[BaseTool]:
    return [_wrap_tool(tool) for tool in tools]


def _wrap_tool(tool: BaseTool) -> BaseTool:
    if not isinstance(tool, StructuredTool):
        return tool

    original_coroutine = tool.coroutine

    async def wrapped_tool(**kwargs: Any) -> Any:
        await emit_tool_event(
            ToolCallEvent(
                phase="start",
                tool_name=tool.name,
                arguments=normalize_tool_output(kwargs),
            )
        )
        try:
            if original_coroutine is None:
                result = await tool.ainvoke(kwargs)
            else:
                result = await original_coroutine(**kwargs)
        except Exception as exc:
            normalized_error = normalize_tool_error(exc)
            await emit_tool_event(
                ToolCallEvent(
                    phase="error",
                    tool_name=tool.name,
                    arguments=normalize_tool_output(kwargs),
                    preview=tool_preview(normalized_error),
                )
            )
            return normalized_error
        normalized_result = normalize_tool_output(result)
        await emit_tool_event(
            ToolCallEvent(
                phase="success",
                tool_name=tool.name,
                arguments=normalize_tool_output(kwargs),
                preview=tool_preview(normalized_result),
            )
        )
        return normalized_result

    return cast(BaseTool, tool.model_copy(update={"coroutine": wrapped_tool, "func": None}))


def set_tool_event_observer(observer: ToolEventObserver | None) -> Token[ToolEventObserver | None]:
    return _tool_event_observer.set(observer)


def reset_tool_event_observer(token: Token[ToolEventObserver | None]) -> None:
    _tool_event_observer.reset(token)


async def emit_tool_event(event: ToolCallEvent) -> None:
    observer = _tool_event_observer.get()
    if observer is not None:
        await observer(event)


def normalize_tool_output(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (Neo4jDate, Neo4jDateTime, date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: normalize_tool_output(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_tool_output(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_tool_output(item) for item in value)
    if isinstance(value, set):
        return [normalize_tool_output(item) for item in value]
    return str(value)


def normalize_tool_error(error: Exception) -> dict[str, str]:
    return {
        "error": error.__class__.__name__,
        "message": str(error),
        "hint": (
            "This tool call failed. Use the error message to correct the arguments, "
            "resolve required ids first, or choose a more appropriate tool."
        ),
    }


def tool_preview(value: Any) -> str:
    rendered = str(value)
    if len(rendered) <= MAX_TOOL_PREVIEW_LENGTH:
        return rendered
    return f"{rendered[:MAX_TOOL_PREVIEW_LENGTH].rstrip()}..."
