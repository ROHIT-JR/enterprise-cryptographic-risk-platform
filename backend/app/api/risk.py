from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.serializers import serialize_risk
from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models import Asset, Project, RiskFinding, User
from backend.app.schemas.common import DistributionItem
from backend.app.schemas.risk import RiskPage

router = APIRouter(prefix="/risks", tags=["Intelligence"])


@router.get("", response_model=RiskPage)
def list_risks(
    project_id: str | None = None,
    severity: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RiskPage:
    """List risk findings, highest score first, with their asset and project context.

    Filter by project or severity. Scores are deterministic: every finding carries the rules that
    produced it.
    """
    filters = []
    if isinstance(user, User):
        filters.append(RiskFinding.organization_id == user.organization_id)
    if project_id:
        filters.append(RiskFinding.project_id == project_id)
    if severity:
        filters.append(RiskFinding.severity == severity)

    base = (
        select(RiskFinding, Asset, Project)
        .join(Asset, RiskFinding.asset_id == Asset.id)
        .join(Project, RiskFinding.project_id == Project.id)
    )
    count_statement = select(func.count(RiskFinding.id))
    if filters:
        base = base.where(*filters)
        count_statement = count_statement.where(*filters)
    total = db.scalar(count_statement) or 0
    rows = db.execute(
        base.order_by(RiskFinding.score.desc(), RiskFinding.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return RiskPage(
        items=[serialize_risk(risk, asset, project) for risk, asset, project in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/distribution", response_model=list[DistributionItem])
def risk_distribution(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[DistributionItem]:
    """Return finding counts per severity (critical, high, medium, low)."""
    statement = select(RiskFinding.severity, func.count(RiskFinding.id))
    if isinstance(user, User):
        statement = statement.where(RiskFinding.organization_id == user.organization_id)
    counts = dict(
        db.execute(
            statement.group_by(RiskFinding.severity)
        ).all()
    )
    return [
        DistributionItem(name=severity, value=counts.get(severity, 0))
        for severity in ("critical", "high", "medium", "low")
    ]
