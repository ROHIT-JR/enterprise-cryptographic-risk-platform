import json
import os
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db

router = APIRouter(prefix="/analytics/validation", tags=["Validation"])

@router.get("", response_model=Dict[str, Any])
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
        with open(baseline_file, "r") as fp:
            res = json.load(fp)

        # Optional: Filter logic if size or scenario are provided
        if size and "experiments" in res:
            res["experiments"] = [exp for exp in res["experiments"] if exp.get("nodes") == size]

        return {"data": res, "message": "Benchmark results fetched.", "status": "success"}
    except Exception as e:
        return {"data": {}, "message": str(e), "status": "error"}
