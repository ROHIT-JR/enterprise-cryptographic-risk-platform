from typing import Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import User
from backend.app.services.audit_service import record_audit
from backend.app.services.report_service import ReportService, ReportType

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{report_type}")
def export_report(
    report_type: ReportType,
    format: Literal["json", "pdf", "cbom"] = "json",
    user: User = Depends(require_permissions(Permission.EXPORT_FINDINGS)),
    db: Session = Depends(get_db),
) -> Response:
    service = ReportService()
    if format == "cbom":
        document = service.cbom(db, organization_id=user.organization_id)
        body = service.json_bytes(document)
        media_type = "application/vnd.ecdat.cbom+json"
        suffix = "json"
    else:
        document = service.build(
            db, organization_id=user.organization_id, report_type=report_type
        )
        body = service.pdf_bytes(document) if format == "pdf" else service.json_bytes(document)
        media_type = "application/pdf" if format == "pdf" else "application/json"
        suffix = format
    record_audit(
        db,
        action="report.exported",
        organization_id=user.organization_id,
        user=user,
        metadata={"report_type": report_type, "format": format},
    )
    db.commit()
    return Response(
        content=body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="ecdat-{report_type}.{suffix}"'},
    )
