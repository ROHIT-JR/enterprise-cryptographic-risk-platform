from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions, resolve_org_id
from backend.app.auth.passwords import hash_password
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import User
from backend.app.schemas.auth import UserCreate, UserResponse
from backend.app.services.audit_service import record_audit

router = APIRouter(prefix="/users", tags=["user management"])


@router.get("", response_model=list[UserResponse])
def list_users(
    organization_id: str | None = Query(default=None),
    administrator: User = Depends(require_permissions(Permission.MANAGE_USERS)),
    db: Session = Depends(get_db),
) -> list[User]:
    target_org_id = resolve_org_id(administrator, organization_id)
    return list(
        db.scalars(
            select(User).where(User.organization_id == target_org_id).order_by(User.created_at)
        )
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    administrator: User = Depends(require_permissions(Permission.MANAGE_USERS)),
    db: Session = Depends(get_db),
) -> User:
    target_org_id = resolve_org_id(administrator, payload.organization_id)
    duplicate = db.scalar(
        select(User).where(
            User.organization_id == target_org_id,
            (
                (func.lower(User.username) == payload.username.lower())
                | (func.lower(User.email) == payload.email.lower())
            ),
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Username or email already exists")
    user = User(
        organization_id=target_org_id,
        username=payload.username,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role.value,
    )
    db.add(user)
    db.flush()
    record_audit(
        db,
        action="user.created",
        organization_id=target_org_id,
        user=administrator,
        metadata={
            "created_user_id": user.id,
            "role": user.role,
            "cross_org": target_org_id != administrator.organization_id,
        },
    )
    db.commit()
    db.refresh(user)
    return user
