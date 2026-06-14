from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: str
    username: str
    password_hash: str


class SignUpRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)
    signup_key: str = Field(min_length=1)


class SignInRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class AuthUserResponse(BaseModel):
    id: str
    username: str


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse
