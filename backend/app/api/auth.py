from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.service import AuthenticationService
from backend.app.database import get_db
from backend.app.models import User
from backend.app.openapi_docs import COMMON_RESPONSES, RATE_LIMITED
from backend.app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **RATE_LIMITED,
        409: {"description": "An organization with that name already exists."},
    },
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Create an organization and its first administrator, and return a token pair.

    Registration is the only way to create an organization. The new user receives the
    `administrator` role; further users are added with `POST /api/v1/users`.
    """
    return AuthenticationService().register(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        **RATE_LIMITED,
        401: {
            "description": "Unknown organization, username or wrong password. The message does "
            "not say which, so it cannot be used to discover accounts.",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid organization, username, or password"}
                }
            },
        },
    },
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange organization, username and password for an access and refresh token pair.

    The access token is a short-lived JWT carrying the user's role and organization. Send it as
    `Authorization: Bearer <access_token>` on every other endpoint.
    """
    return AuthenticationService().login(db, payload)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        **RATE_LIMITED,
        401: {
            "description": "The refresh token is invalid, expired, revoked (including because "
            "it was already used) or belongs to a disabled user.",
            "content": {
                "application/json": {"example": {"detail": "Refresh token is expired or revoked"}}
            },
        },
    },
)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange a refresh token for a new token pair.

    Refresh tokens rotate: the submitted token is revoked as part of the exchange, so replaying it
    returns `401`. Store only the newest pair.
    """
    return AuthenticationService().refresh(db, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=COMMON_RESPONSES)
def logout(
    payload: RefreshRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Revoke a refresh token. The matching access token stays valid until it expires."""
    AuthenticationService().revoke(db, payload.refresh_token, user)


@router.get("/me", response_model=UserResponse, responses=COMMON_RESPONSES)
def me(user: User = Depends(get_current_user)) -> User:
    """Return the profile, role and organization of the authenticated user."""
    return user
