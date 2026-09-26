from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions, resolve_org_id
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import AuditLog, User
from backend.app.schemas.enterprise import AuditLogResponse
from backend.app.services.audit_service import record_audit

router = APIRouter(prefix="/audit-logs", tags=["Enterprise"])


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    organization_id: str | None = Query(default=None),
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(require_permissions(Permission.VIEW_REPORTS)),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    """Return the organization's audit trail, newest first.

    Records authentication, scan, report-export and configuration events with the acting user.
    Requires the `view_reports` permission, so auditors can read it. Platform admins may pass
    `organization_id` to view another organization's trail; every such cross-org view is itself
    recorded in that organization's audit trail.
    """
    target_org_id = resolve_org_id(user, organization_id)
    if target_org_id != user.organization_id:
        record_audit(
            db,
            action="audit_log.viewed_cross_org",
            organization_id=target_org_id,
            user=user,
            metadata={"viewed_by_platform_admin": user.id},
        )
        db.commit()
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == target_org_id)
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
