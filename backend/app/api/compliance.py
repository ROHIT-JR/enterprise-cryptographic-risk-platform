from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import User
from backend.app.schemas.compliance import NQMComplianceReport
from backend.app.services.compliance_service import build_compliance_report

router = APIRouter(prefix="/compliance", tags=["Enterprise"])


@router.get("/nqm", response_model=NQMComplianceReport)
def get_nqm_compliance(
    user: User = Depends(require_permissions(Permission.VIEW_DASHBOARD)),
    db: Session = Depends(get_db),
) -> NQMComplianceReport:
    """India NQM phase alignment, computed from this organization's live inventory."""
    return NQMComplianceReport(**build_compliance_report(db, user.organization_id))
