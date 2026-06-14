import asyncio
from typing import Any, cast

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from corporate_rag.settings import AgentSettings


class AgentModelConfigurationError(RuntimeError):
    pass


async def initialize_chat_model(model_id: str, settings: AgentSettings) -> BaseChatModel:
    kwargs: dict[str, Any] = {}
    if model_id.startswith("openai:"):
        if not settings.openai_api_key:
            raise AgentModelConfigurationError(
                "OpenAI agent models require CORPORATE_RAG_AGENT_OPENAI_API_KEY "
                "or OPENAI_API_KEY."
        )
        kwargs["api_key"] = settings.openai_api_key

    def initialize() -> BaseChatModel:
        return cast(BaseChatModel, init_chat_model(model_id, **kwargs))

    return await asyncio.to_thread(initialize)
