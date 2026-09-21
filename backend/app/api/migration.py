from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.database import get_db
from backend.app.models import Asset, MigrationPlan, RiskAnalysis, User
from backend.app.schemas.intelligence import (
    MigrationRecommendationResponse,
    MigrationRoadmapResponse,
    MigrationRoadmapWave,
)

router = APIRouter(prefix="/migration", tags=["Migration"])


def _recommendation(
    plan: MigrationPlan,
    asset: Asset,
    analysis: RiskAnalysis | None,
) -> MigrationRecommendationResponse:
    return MigrationRecommendationResponse(
        asset_id=asset.id,
        asset_name=asset.name,
        asset_type=asset.asset_type,
        current_algorithm=asset.algorithm or asset.name,
        recommended_algorithm=plan.recommended_algorithm,
        wave=plan.wave,
        complexity=plan.complexity,
        risk_score=analysis.final_score if analysis else None,
        reasons=plan.reasons,
        recommendation=plan.recommendation,
    )


def _rows(
    db: Session, project_id: str | None = None, organization_id: str | None = None
):
    statement = (
        select(MigrationPlan, Asset, RiskAnalysis)
        .join(Asset, MigrationPlan.asset_id == Asset.id)
        .outerjoin(RiskAnalysis, RiskAnalysis.asset_id == Asset.id)
    )
    if project_id:
        statement = statement.where(MigrationPlan.project_id == project_id)
    if organization_id:
        statement = statement.where(MigrationPlan.organization_id == organization_id)
    return db.execute(statement.order_by(MigrationPlan.wave, Asset.name)).all()


@router.get("/recommendations", response_model=list[MigrationRecommendationResponse])
def get_recommendations(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MigrationRecommendationResponse]:
    """Return the PQC migration recommendation for every planned asset.

    Each recommendation names the target algorithm chosen by the TOPSIS engine, its migration wave
    and complexity, and the reasoning behind it.
    """
    organization_id = user.organization_id if isinstance(user, User) else None
    return [_recommendation(*row) for row in _rows(db, project_id, organization_id)]


@router.get("/roadmap", response_model=MigrationRoadmapResponse)
def get_roadmap(
    project_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MigrationRoadmapResponse:
    """Return the migration plan grouped into dependency-ordered waves.

    Trust anchors and cryptographic primitives migrate before the services that consume them, so a
    wave only starts once the wave it depends on can pass interoperability testing.
    """
    organization_id = user.organization_id if isinstance(user, User) else None
    items = [_recommendation(*row) for row in _rows(db, project_id, organization_id)]
    grouped: dict[int, list[MigrationRecommendationResponse]] = defaultdict(list)
    for item in items:
        grouped[item.wave].append(item)
    titles = {
        1: "Trust and cryptographic foundations",
        2: "Direct dependents and shared services",
    }
    waves = [
        MigrationRoadmapWave(
            wave=wave,
            title=titles.get(wave, "Dependent applications"),
            reason=(
                "Migrate dependencies first to preserve service compatibility."
                if wave == 1
                else "Begin after the previous wave passes interoperability validation."
            ),
            items=wave_items,
        )
        for wave, wave_items in sorted(grouped.items())
    ]
    return MigrationRoadmapResponse(total_assets=len(items), waves=waves)
