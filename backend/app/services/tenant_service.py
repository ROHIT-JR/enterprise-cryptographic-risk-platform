from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Organization, User

LEGACY_ORGANIZATION = "Local Workspace"


def resolve_organization_id(db: Session, principal: object) -> str:
    if isinstance(principal, User):
        return principal.organization_id
    organization = db.scalar(select(Organization).where(Organization.name == LEGACY_ORGANIZATION))
    if not organization:
        organization = Organization(name=LEGACY_ORGANIZATION, industry="Development")
        db.add(organization)
        db.flush()
    return organization.id
