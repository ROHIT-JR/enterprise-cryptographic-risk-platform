from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models import (
    Asset,
    AuditLog,
    MigrationPlan,
    Project,
    RiskFinding,
    Scan,
    User,
)
from backend.app.schemas.enterprise import AuditLogResponse, EnterpriseOverview

router = APIRouter(prefix="/enterprise", tags=["Enterprise"])


@router.get("/overview", response_model=EnterpriseOverview)
def enterprise_overview(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> EnterpriseOverview:
    """Return organization-wide totals for the administrator dashboard.

    Counts organizations, users, projects, scans, assets, critical risks and assets in migration,
    alongside the most recent audit events.
    """
    organization_id = user.organization_id
    recent = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(8)
        )
    )
    return EnterpriseOverview(
        organizations=1,
        users=db.scalar(select(func.count(User.id)).where(User.organization_id == organization_id))
        or 0,
        projects=db.scalar(
            select(func.count(Project.id)).where(Project.organization_id == organization_id)
        )
        or 0,
        scans=db.scalar(select(func.count(Scan.id)).where(Scan.organization_id == organization_id))
        or 0,
        assets=db.scalar(
            select(func.count(Asset.id)).where(Asset.organization_id == organization_id)
        )
        or 0,
        critical_risks=db.scalar(
            select(func.count(RiskFinding.id)).where(
                RiskFinding.organization_id == organization_id,
                RiskFinding.severity == "critical",
            )
        )
        or 0,
        migration_assets=db.scalar(
            select(func.count(MigrationPlan.id)).where(
                MigrationPlan.organization_id == organization_id
            )
        )
        or 0,
        recent_audit=[
            AuditLogResponse(
                id=item.id,
                user_id=item.user_id,
                action=item.action,
                timestamp=item.timestamp,
                metadata=item.event_metadata,
            )
            for item in recent
        ],
    )
