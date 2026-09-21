from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import Organization, User
from backend.app.schemas.auth import OrganizationResponse, OrganizationUpdate
from backend.app.services.audit_service import record_audit

router = APIRouter(prefix="/organizations", tags=["Enterprise"])


@router.get("/current", response_model=OrganizationResponse)
def current_organization(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Organization:
    """Return the caller's organization, including its industry and settings."""
    organization = db.get(Organization, user.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.put("/current", response_model=OrganizationResponse)
def update_organization(
    payload: OrganizationUpdate,
    user: User = Depends(require_permissions(Permission.CONFIGURE_ORGANIZATION)),
    db: Session = Depends(get_db),
) -> Organization:
    """Update the caller's organization. Requires the `configure_organization` permission."""
    duplicate = db.scalar(
        select(Organization).where(
            func.lower(Organization.name) == payload.name.lower(),
            Organization.id != user.organization_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Organization name already exists")
    organization = db.get(Organization, user.organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    organization.name = payload.name
    organization.industry = payload.industry
    record_audit(
        db,
        action="organization.updated",
        organization_id=organization.id,
        user=user,
        metadata={"name": organization.name},
    )
    db.commit()
    db.refresh(organization)
    return organization
