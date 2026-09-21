from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import AuditLog, User
from backend.app.schemas.enterprise import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["Enterprise"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(require_permissions(Permission.VIEW_REPORTS)),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    """Return the organization's audit trail, newest first.

    Records authentication, scan, report-export and configuration events with the acting user.
    Requires the `view_reports` permission, so auditors can read it.
    """
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == user.organization_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    return [
        AuditLogResponse(
            id=row.id,
            user_id=row.user_id,
            action=row.action,
            timestamp=row.timestamp,
            metadata=row.event_metadata,
        )
        for row in rows
    ]
