from typing import Literal

from pydantic import BaseModel, Field

from corporate_rag.corporate_agent.prompt import DEFAULT_AGENT_VERSION, agent_version_options
from corporate_rag.settings import AgentSettings

AgentModeId = Literal["corporate", "law"]

CORPORATE_STARTERS = [
    ("Current board", "Who is on the board of Acer European Holdings today?"),
    ("Capital contribution", "Find documents about capital contributions in 2022."),
    ("Corpus overview", "What business subjects does this corpus cover?"),
    (
        "Key resolutions",
        "What shareholder or board resolutions are mentioned for Acer European Holdings?",
    ),
    (
        "Executive timeline",
        "Who served as director of Acer European Holdings over time, "
        "and what evidence supports it?",
    ),
    (
        "Transaction history",
        "Give me the history of any transaction between Acer European Holdings "
        "and Acer Sales International SA.",
    ),
]

LAW_STARTERS = [
    (
        "AG formation",
        "Under the Swiss Code of Obligations, what are the minimum "
        "formation requirements for a Swiss stock corporation?",
    ),
    (
        "Board duties",
        "What are the legal duties and core powers of the board of "
        "directors under the Swiss Code of Obligations?",
    ),
    (
        "Commercial register",
        "What information about directors, signatories, and representation "
        "powers must be filed in the Swiss commercial register?",
    ),
    (
        "Merger Act structures",
        "Under the Swiss Merger Act, what is the difference between a merger, "
        "a demerger, a conversion, and a transfer of assets?",
    ),
    (
        "Director liability",
        "When can corporate directors incur liability under the Swiss Code of "
        "Obligations for breach of duty, and who can bring the claim?",
    ),
    (
        "Foreign company law",
        "Under the Swiss Federal Act on Private International Law, which law "
        "governs a company incorporated abroad but operating in Switzerland?",
    ),
]


class AgentMode(BaseModel):
    id: AgentModeId
    label: str
    supports_agent_versions: bool
    supports_citations: bool


class AgentModelOption(BaseModel):
    id: str
    label: str
    default: bool = False


class AgentVersionOption(BaseModel):
    id: str
    label: str
    default: bool = False


class AgentStarter(BaseModel):
    label: str
    message: str


class AgentConfigResponse(BaseModel):
    runtime_path: str
    default_mode: AgentModeId
    default_model_id: str
    default_agent_version: str
    modes: list[AgentMode]
    models: list[AgentModelOption]
    agent_versions: list[AgentVersionOption]
    starters: dict[AgentModeId, list[AgentStarter]]


class AgentHandoffResponse(BaseModel):
    runtime_path: str
    header_auth_path: str
    websocket_path: str
    expires_in_seconds: int = Field(gt=0)


def _starters(pairs: list[tuple[str, str]]) -> list[AgentStarter]:
    return [AgentStarter(label=label, message=message) for label, message in pairs]


def model_options(settings: AgentSettings) -> list[tuple[str, str]]:
    options = [
        ("Default", settings.default_model_id),
        ("OpenAI GPT-5.5", "openai:gpt-5.5"),
        ("OpenAI GPT-5.4", "openai:gpt-5.4"),
        ("OpenAI GPT-5.4 mini", "openai:gpt-5.4-mini"),
        ("OpenAI GPT-4.1", "openai:gpt-4.1"),
    ]
    deduped: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, model_id in options:
        if model_id in seen:
            continue
        seen.add(model_id)
        deduped.append((label, model_id))
    return deduped


def starters_for_mode(mode: AgentModeId) -> list[AgentStarter]:
    return _starters(LAW_STARTERS if mode == "law" else CORPORATE_STARTERS)


def default_chat_settings(settings: AgentSettings) -> dict[str, str]:
    return {
        "Mode": "corporate",
        "Model": settings.default_model_id,
        "AgentVersion": DEFAULT_AGENT_VERSION,
    }


def build_agent_config(settings: AgentSettings) -> AgentConfigResponse:
    return AgentConfigResponse(
        runtime_path=settings.chainlit_mount_path,
        default_mode="corporate",
        default_model_id=settings.default_model_id,
        default_agent_version=DEFAULT_AGENT_VERSION,
        modes=[
            AgentMode(
                id="corporate",
                label="Corporate archive",
                supports_agent_versions=True,
                supports_citations=True,
            ),
            AgentMode(
                id="law",
                label="Swiss law",
                supports_agent_versions=False,
                supports_citations=True,
            ),
        ],
        models=[
            AgentModelOption(
                id=model_id,
                label=label,
                default=model_id == settings.default_model_id,
            )
            for label, model_id in model_options(settings)
        ],
        agent_versions=[
            AgentVersionOption(
                id=version_id,
                label=label,
                default=version_id == DEFAULT_AGENT_VERSION,
            )
            for label, version_id in agent_version_options()
        ],
        starters={
            "corporate": _starters(CORPORATE_STARTERS),
            "law": _starters(LAW_STARTERS),
        },
    )
