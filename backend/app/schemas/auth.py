from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.app.auth.permissions import Role


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    organization: str = Field(min_length=2, max_length=160)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=4096)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)
    role: Role


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    organization_id: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse


class OrganizationResponse(BaseModel):
    id: str
    name: str
    industry: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    industry: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())
