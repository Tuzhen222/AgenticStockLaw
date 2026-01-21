"""
Token schemas for authentication.
"""
from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    """Access token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: Optional[str] = None
    type: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema."""
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str
