from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models import Asset, BusinessContext, RiskAnalysis, User
from backend.app.schemas.mosca import (
    MoscaAssetResult,
    MoscaSimulateRequest,
    MoscaSimulateResponse,
)
from risk_engine.mosca_model import MoscaModel

router = APIRouter(prefix="/mosca", tags=["mosca"])

# Buckets translating a 0-100 migration-complexity score into a rough number
# of years the migration itself is expected to take.
_COMPLEXITY_YEARS = ((30, 0.5), (60, 1.5), (80, 3.0), (101, 5.0))


def _migration_years(score: float) -> float:
    for ceiling, years in _COMPLEXITY_YEARS:
        if score <= ceiling:
            return years
    return 5.0


@router.post("/simulate", response_model=MoscaSimulateResponse)
def simulate_mosca(
    payload: MoscaSimulateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MoscaSimulateResponse:
    model = MoscaModel()
    statement = (
        select(RiskAnalysis, Asset, BusinessContext)
        .join(Asset, RiskAnalysis.asset_id == Asset.id)
        .outerjoin(BusinessContext, BusinessContext.asset_id == Asset.id)
    )
    if isinstance(user, User):
        statement = statement.where(RiskAnalysis.organization_id == user.organization_id)
    if payload.project_id:
        statement = statement.where(RiskAnalysis.project_id == payload.project_id)
    rows = db.execute(statement.order_by(RiskAnalysis.final_score.desc())).all()

    current_year = datetime.date.today().year
    years_until_quantum = max(payload.quantum_arrival_year - current_year, 1)

    items: list[MoscaAssetResult] = []
    for analysis, asset, context in rows:
        data_lifetime = float(context.data_lifetime_years) if context else 5.0
        migration_years = _migration_years(analysis.migration_complexity_score)
        sim = model.simulate(
            data_lifetime=data_lifetime,
            migration_time=migration_years,
            quantum_arrival_year=payload.quantum_arrival_year,
            current_year=current_year,
        )
        quantum_vulnerable = analysis.quantum_classification in {"critical", "high"}
        if not quantum_vulnerable:
            verdict = "safe"
        elif sim["verdict"] == "critical":
            verdict = "critical"
        else:
            verdict = "plan"
        items.append(
            MoscaAssetResult(
                asset_id=asset.id,
                asset_name=asset.name,
                algorithm=asset.algorithm,
                data_lifetime_years=data_lifetime,
                migration_time_years=migration_years,
                lhs=sim["lhs"],
                verdict=verdict,
            )
        )

    items.sort(key=lambda item: item.lhs, reverse=True)
    critical_items = [item for item in items if item.verdict == "critical"]
    plan_items = [item for item in items if item.verdict == "plan"]
    safe_items = [item for item in items if item.verdict == "safe"]
    organization_status = "critical" if critical_items else "plan" if plan_items else "safe"

    return MoscaSimulateResponse(
        organization_status=organization_status,
        quantum_arrival_year=payload.quantum_arrival_year,
        current_year=current_year,
        years_until_quantum=years_until_quantum,
        critical_count=len(critical_items),
        plan_count=len(plan_items),
        safe_count=len(safe_items),
        total_assets=len(items),
        most_urgent_asset=critical_items[0].asset_name if critical_items else None,
        formula=f"Data Lifetime + Migration Time > Years Until Quantum ({years_until_quantum})",
        items=items,
    )
