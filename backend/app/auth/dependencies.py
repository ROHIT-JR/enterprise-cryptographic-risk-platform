from collections.abc import Callable

from fastapi import Depends, HTTPException, status
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

    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permissions(user.role, required):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not permit this operation",
            )
        return user

    return dependency


def tenant_id(user: object) -> str | None:
    return user.organization_id if isinstance(user, User) else None
