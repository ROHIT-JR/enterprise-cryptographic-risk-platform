from __future__ import annotations

from functools import cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Asset, MigrationPlan
from migration_engine.verification import (
    MigrationVerificationReport,
    MigrationVerifier,
    PlanView,
)


@cache
def _verifier() -> MigrationVerifier:
    return MigrationVerifier()


def build_verification_report(
    db: Session, organization_id: str, project_id: str | None = None
) -> MigrationVerificationReport:
    """Verify every migration plan the organisation owns (optionally for one project)."""
    statement = (
        select(MigrationPlan, Asset)
        .join(Asset, MigrationPlan.asset_id == Asset.id)
        .where(MigrationPlan.organization_id == organization_id)
    )
    if project_id:
        statement = statement.where(MigrationPlan.project_id == project_id)
    rows = db.execute(statement.order_by(MigrationPlan.wave, Asset.name)).all()

    verifier = _verifier()
    plans = [
        PlanView(
            asset_id=asset.id,
            asset_name=asset.name,
            asset_type=asset.asset_type,
            wave=plan.wave,
            current_algorithm=asset.algorithm or asset.name,
            recommended_algorithm=plan.recommended_algorithm,
            constraints=[str(item) for item in (plan.constraints or [])],
            recommendation=dict(plan.recommendation or {}),
        )
        for plan, asset in rows
    ]
    return verifier.report(verifier.verify_many(plans))
