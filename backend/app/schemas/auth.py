from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.auth.permissions import Role


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "organization_name": "Acme Bank",
                    "industry": "Financial services",
                    "username": "acme-admin",
                    "email": "admin@acme.example",
                    "password": "<at least 12 characters>",
                }
            ]
        }
    )


class LoginRequest(BaseModel):
    organization: str = Field(min_length=2, max_length=160)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=256)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "organization": "SecureBank",
                    "username": "security-analyst",
                    "password": "<your password>",
                }
            ]
        }
    )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=4096)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"refresh_token": "<the refresh_token returned by POST /auth/login>"}]
        }
    )


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=12, max_length=256)
    role: Role
    # Only honored when the caller is the platform admin (see
    # backend.app.auth.dependencies.resolve_org_id) — ignored for every
    # ordinary org administrator, who can only ever create users in their
    # own organization regardless of what they send here.
    organization_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "new-analyst",
                    "email": "analyst@acme.example",
                    "password": "<at least 12 characters>",
                    "role": "security_analyst",
                }
            ]
        }
    )


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    organization_id: str
    is_active: bool
    is_platform_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserResponse

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "<JWT access token>",
                    "refresh_token": "<refresh token>",
                    "token_type": "bearer",
                    "expires_in": 900,
                    "user": {
                        "id": "0b6f6f0e-6b1f-4c1e-9d55-0d1c2f6a7e11",
                        "username": "security-analyst",
                        "email": "analyst@securebank.demo",
                        "role": "security_analyst",
                        "organization_id": "7c2d9a54-3b1e-4f60-8a37-5e9d1c0b4a22",
                        "is_active": True,
                        "created_at": "2026-09-01T09:30:00Z",
                    },
                }
            ]
        }
    )


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

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"name": "Acme Bank", "industry": "Financial services"}]}
    )


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    industry: str | None = Field(default=None, max_length=120)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())
