from typing import Annotated

from fastapi import APIRouter, Depends, Response

from corporate_rag.agents.catalog import (
    AgentConfigResponse,
    AgentHandoffResponse,
    build_agent_config,
)
from corporate_rag.agents.handoff import create_handoff_token
from corporate_rag.app.dependencies import agent_settings, auth_settings, current_user
from corporate_rag.auth.models import AuthUser
from corporate_rag.settings import AgentSettings, AuthSettings

router = APIRouter(
    prefix="/agent",
    tags=["agents"],
)


@router.get(
    "/config",
    response_model=AgentConfigResponse,
    summary="Return native agent UI configuration",
)
async def agent_config(
    settings: Annotated[AgentSettings, Depends(agent_settings)],
) -> AgentConfigResponse:
    return build_agent_config(settings)


@router.post(
    "/handoff",
    response_model=AgentHandoffResponse,
    summary="Authorize the Chainlit runtime for the current product user",
)
async def create_agent_handoff(
    response: Response,
    user: Annotated[AuthUser, Depends(current_user)],
    auth_config: Annotated[AuthSettings, Depends(auth_settings)],
    settings: Annotated[AgentSettings, Depends(agent_settings)],
) -> AgentHandoffResponse:
    token = create_handoff_token(user, auth_settings=auth_config, agent_settings=settings)
    response.set_cookie(
        settings.handoff_cookie_name,
        token,
        max_age=settings.handoff_token_ttl_seconds,
        path=settings.chainlit_mount_path,
        httponly=True,
        secure=settings.secure_handoff_cookie,
        samesite="lax",
    )
    return AgentHandoffResponse(
        runtime_path=settings.chainlit_mount_path,
        header_auth_path=f"{settings.chainlit_mount_path}/auth/header",
        websocket_path=f"{settings.chainlit_mount_path}/ws/socket.io",
        expires_in_seconds=settings.handoff_token_ttl_seconds,
    )
