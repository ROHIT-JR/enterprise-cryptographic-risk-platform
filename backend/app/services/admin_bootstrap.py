from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.passwords import hash_password
from backend.app.auth.permissions import Role
from backend.app.models import Organization, User

logger = logging.getLogger(__name__)

PLATFORM_ORGANIZATION_NAME = "Platform"


def bootstrap_platform_admin(db: Session, username: str, password: str) -> None:
    """Ensure a predefined platform administrator account exists.

    Runs on every startup but only ever creates the account once — if it
    already exists, this is a no-op so a later password change (made some
    other way) is never silently overwritten by a stale env var.
    """
    organization = db.scalar(
        select(Organization).where(Organization.name == PLATFORM_ORGANIZATION_NAME)
    )
    if not organization:
        organization = Organization(name=PLATFORM_ORGANIZATION_NAME, industry="Platform Operations")
        db.add(organization)
        db.flush()

    existing = db.scalar(
        select(User).where(
            User.organization_id == organization.id,
            User.username == username,
        )
    )
    if existing:
        # Self-heal accounts bootstrapped before is_platform_admin existed —
        # never touches username/email/password, only this one flag.
        if not existing.is_platform_admin:
            existing.is_platform_admin = True
            db.commit()
            logger.info("platform_admin_flag_backfilled username=%s", username)
        return

    admin = User(
        organization_id=organization.id,
        username=username,
        email=f"{username}@platform.local",
        password_hash=hash_password(password),
        role=Role.ADMINISTRATOR.value,
        is_platform_admin=True,
    )
    db.add(admin)
    db.commit()
    logger.info("platform_admin_bootstrapped username=%s", username)
