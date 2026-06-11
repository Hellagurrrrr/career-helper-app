from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import CamelModel


class RegisterRequest(BaseModel):
    # Business validation (exact messages) handled in the router, so fields are lenient here.
    name: str = ""
    email: str = ""
    password: str = ""


class LoginRequest(BaseModel):
    email: str = ""
    password: str = ""


class RefreshRequest(CamelModel):
    refresh_token: str


class AuthUser(CamelModel):
    id: str
    email: str
    name: str
    created_at: int


class AuthTokens(CamelModel):
    access_token: str
    refresh_token: str


class AuthResponse(CamelModel):
    user: AuthUser
    tokens: AuthTokens
