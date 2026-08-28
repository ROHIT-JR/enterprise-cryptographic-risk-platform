from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Asset, RiskFinding, Scan
from backend.app.schemas.common import DistributionItem
from backend.app.schemas.dashboard import DashboardMetrics, DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    crypto_types = ("algorithm", "library", "certificate", "protocol", "configuration")
    metrics = DashboardMetrics(
        total_assets=db.scalar(
            select(func.count(Asset.id)).where(Asset.asset_type.in_(crypto_types))
        )
        or 0,
        critical_assets=db.scalar(
            select(func.count(RiskFinding.id)).where(RiskFinding.severity == "critical")
        )
        or 0,
        algorithms_found=db.scalar(
            select(func.count(distinct(Asset.algorithm))).where(Asset.algorithm.is_not(None))
        )
        or 0,
        projects_scanned=db.scalar(
            select(func.count(distinct(Scan.project_id))).where(Scan.status == "completed")
        )
        or 0,
    )
    risk_counts = dict(
        db.execute(
            select(RiskFinding.severity, func.count(RiskFinding.id)).group_by(RiskFinding.severity)
        ).all()
    )
    algorithm_rows = db.execute(
        select(Asset.algorithm, func.count(Asset.id).label("count"))
        .where(Asset.algorithm.is_not(None))
        .group_by(Asset.algorithm)
        .order_by(func.count(Asset.id).desc())
        .limit(8)
    ).all()
    recent_scans = list(db.scalars(select(Scan).order_by(Scan.created_at.desc()).limit(6)))
    return DashboardResponse(
        metrics=metrics,
        risk_distribution=[
            DistributionItem(name=severity, value=risk_counts.get(severity, 0))
            for severity in ("critical", "high", "medium", "low")
        ],
        algorithm_distribution=[
            DistributionItem(name=algorithm or "Unknown", value=count)
            for algorithm, count in algorithm_rows
        ],
        recent_scans=recent_scans,
    )
