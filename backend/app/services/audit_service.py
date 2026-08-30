from typing import Any

from sqlalchemy.orm import Session

from backend.app.models import AuditLog, User


def record_audit(
    db: Session,
    *,
    action: str,
    organization_id: str,
    user: User | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        organization_id=organization_id,
        user_id=user.id if user else None,
        action=action,
        event_metadata=metadata or {},
    )
    db.add(entry)
    db.flush()
    return entry
