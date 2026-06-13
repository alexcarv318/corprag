from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from corporate_rag.app.dependencies import app_settings
from corporate_rag.settings import AppSettings


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str


def build_health_response(settings: AppSettings) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
    )


router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    description="Returns basic liveness metadata for local and deployed smoke tests.",
)
async def health(settings: Annotated[AppSettings, Depends(app_settings)]) -> HealthResponse:
    return build_health_response(settings)
