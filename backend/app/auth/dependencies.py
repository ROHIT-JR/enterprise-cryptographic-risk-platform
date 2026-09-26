from collections.abc import Callable

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.auth.permissions import Permission, has_permissions
from backend.app.auth.tokens import TokenError, decode_token
from backend.app.database import get_db
from backend.app.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid authentication is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        claims = decode_token(credentials.credentials)
    except TokenError as exc:
        raise unauthorized from exc
    if claims["type"] != "access":
        raise unauthorized
    user = db.get(User, claims["sub"])
    if (
        not user
        or not user.is_active
        or user.organization_id != claims["org"]
        or user.role != claims["role"]
    ):
        raise unauthorized
    return user


def require_permissions(*permissions: Permission) -> Callable[..., User]:
    required = set(permissions)
    # Declared as security scopes so the OpenAPI spec (and Swagger UI) shows, per operation,
    # which permission a caller needs; enforcement is still the has_permissions check below.
    scopes = sorted(permission.value for permission in required)

    def dependency(user: User = Security(get_current_user, scopes=scopes)) -> User:
        if not has_permissions(user.role, required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not permit this operation",
            )
        return user

    return dependency


def require_platform_admin(user: User = Depends(get_current_user)) -> User:
    """Gate an endpoint to the single predefined platform administrator account.

    Deliberately not modeled as a Role — is_platform_admin is a separate
    column so it can never collapse into an ordinary org's ADMINISTRATOR
    permission set (see backend/app/services/admin_bootstrap.py).
    """
    if not user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires platform administrator access",
        )
    return user


def resolve_org_id(user: User, requested_org_id: str | None) -> str:
    """Resolve which organization a request should act on.

    Every caller gets their own organization_id unless they are the
    platform admin AND explicitly requested a different one — this is the
    only place cross-org access is granted anywhere in the app.
    """
    if requested_org_id and user.is_platform_admin:
        return requested_org_id
    return user.organization_id


def tenant_id(user: object) -> str | None:
    return user.organization_id if isinstance(user, User) else None
