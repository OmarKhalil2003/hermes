from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    """Schema for validating user registration input."""

    email: str = Field(..., description="The user's email address")
    password: str = Field(..., min_length=6, description="Minimum 6 character password")
    is_superuser: bool = Field(
        default=False, description="Whether the user is an admin"
    )


class UserOut(BaseModel):
    """Schema representing public user output data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    is_active: bool
    is_superuser: bool
    created_at: datetime


class Token(BaseModel):
    """Schema for OAuth2-compliant authentication token output."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Schema validating access token renewal requests."""

    refresh_token: str


class TokenPayload(BaseModel):
    """Internal model for validating decoded token payloads."""

    sub: str | None = None
    exp: int | None = None
    type: str | None = None
