import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from corporate_rag.app.dependencies import auth_repository, auth_settings, current_user
from corporate_rag.auth.models import (
    AuthTokenResponse,
    AuthUser,
    AuthUserResponse,
    SignInRequest,
    SignUpRequest,
)
from corporate_rag.auth.repository import (
    AuthRepository,
    DuplicateUsernameError,
    InvalidPasswordError,
    InvalidUsernameError,
)
from corporate_rag.auth.tokens import create_access_token
from corporate_rag.settings import AuthSettings

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/sign-up",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a password user",
)
async def sign_up(
    payload: SignUpRequest,
    response: Response,
    repository: Annotated[AuthRepository, Depends(auth_repository)],
    settings: Annotated[AuthSettings, Depends(auth_settings)],
) -> AuthUserResponse:
    if not settings.signup_key:
        raise HTTPException(status_code=404, detail="sign-up is not enabled")
    if not secrets.compare_digest(payload.signup_key, settings.signup_key):
        raise HTTPException(status_code=403, detail="invalid sign-up key")

    try:
        user = repository.create_user(payload.username, payload.password)
    except DuplicateUsernameError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (InvalidUsernameError, InvalidPasswordError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    response.headers["Cache-Control"] = "no-store"
    return AuthUserResponse(id=user.id, username=user.username)


@router.post(
    "/sign-in",
    response_model=AuthTokenResponse,
    summary="Sign in and receive a bearer token",
)
async def sign_in(
    payload: SignInRequest,
    response: Response,
    repository: Annotated[AuthRepository, Depends(auth_repository)],
    settings: Annotated[AuthSettings, Depends(auth_settings)],
) -> AuthTokenResponse:
    user = repository.authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid username or password")

    response.headers["Cache-Control"] = "no-store"
    public_user = AuthUserResponse(id=user.id, username=user.username)
    return AuthTokenResponse(
        access_token=create_access_token(
            user,
            secret_key=settings.secret_key,
            ttl_seconds=settings.access_token_ttl_seconds,
        ),
        user=public_user,
    )


@router.get(
    "/me",
    response_model=AuthUserResponse,
    summary="Return the current password user",
)
async def me(user: Annotated[AuthUser, Depends(current_user)]) -> AuthUserResponse:
    return AuthUserResponse(id=user.id, username=user.username)
