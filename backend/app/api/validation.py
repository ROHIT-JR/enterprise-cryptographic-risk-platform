import json
import os
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import User
from backend.app.services.migration_verification_service import build_verification_report
from migration_engine.verification import MigrationVerificationReport

router = APIRouter(prefix="/analytics/validation", tags=["Research & Validation"])

@router.get("", response_model=dict[str, Any])
def get_validation_results(
    size: int = Query(None, description="Filter by graph size"),
    scenario: str = Query(None, description="Filter by scenario (e.g. mosca, topsis)"),
    db: Session = Depends(get_db),
    actor=Depends(require_permissions(Permission.VIEW_DASHBOARD))
):
    """
    Read-only endpoint exposing pre-generated benchmark results.
    Does NOT trigger benchmarks on the fly to prevent arbitrary CPU exhaustion.
    Uses identical RBAC checking conventions (allows viewer/auditor for read-only analytics).
    """
    results_dir = "benchmarks/results"
    baseline_file = os.path.join(results_dir, "validation_baseline.json")

    if not os.path.exists(baseline_file):
        return {"data": {}, "message": "No benchmarks executed.", "status": "empty"}

    try:
        with open(baseline_file) as fp:
            res = json.load(fp)

        # Optional: Filter logic if size or scenario are provided
        if size and "experiments" in res:
            res["experiments"] = [exp for exp in res["experiments"] if exp.get("nodes") == size]

        return {"data": res, "message": "Benchmark results fetched.", "status": "success"}
    except Exception as e:
        return {"data": {}, "message": str(e), "status": "error"}


@router.get("/migrations", response_model=MigrationVerificationReport)
def get_migration_verification(
    project_id: str | None = Query(None, description="Limit to one project"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(Permission.VIEW_DASHBOARD)),
) -> MigrationVerificationReport:
    """Verification checklist, hybrid path and test results for each PQC migration task.

    Everything is derived from the organisation's stored migration plans, the NIST knowledge
    base and the benchmark reference data. Nothing is executed on request.
    """
    return build_verification_report(db, user.organization_id, project_id)
