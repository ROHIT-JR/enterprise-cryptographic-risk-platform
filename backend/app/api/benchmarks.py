import threading
from functools import cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import require_permissions
from backend.app.auth.permissions import Permission
from backend.app.database import get_db
from backend.app.models import User
from backend.app.services.audit_service import record_audit
from benchmarks import pqc_benchmarks

router = APIRouter(prefix="/benchmarks", tags=["Research & Validation"])

# The host is shared but its details (OS, Python, library versions) are not something one tenant
# should see from another's run, so the latest run is kept per organisation, in process memory.
# Only one run may execute at a time so a burst of requests cannot pin every CPU core.
_run_lock = threading.Lock()
_latest_runs: dict[str, dict[str, Any]] = {}


@cache
def _reference() -> dict[str, Any]:
    return pqc_benchmarks.load_reference()


class BenchmarkRunRequest(BaseModel):
    iterations: int = Field(default=20, ge=1, le=pqc_benchmarks.MAX_ITERATIONS)
    include_pqc: bool = True

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"iterations": 20, "include_pqc": True}]}
    )


def _catalogue(organization_id: str) -> dict[str, Any]:
    reference = _reference()
    latest_run = _latest_runs.get(organization_id)
    measured = (latest_run or {}).get("measured", {})
    rows = pqc_benchmarks.score_algorithms(reference)
    for row in rows:
        row["measured_us"] = measured.get(row["name"])
    return {
        "schema_version": reference["schema_version"],
        "description": reference["description"],
        "sources": reference["sources"],
        "tls_model": reference["tls_model"],
        "algorithms": rows,
        "latest_run": latest_run,
    }


@router.get("/pqc")
def get_pqc_benchmarks(
    user: User = Depends(require_permissions(Permission.VIEW_DASHBOARD)),
) -> dict[str, Any]:
    """Reference PQC/classical benchmark data, plus this organisation's latest live run."""
    return _catalogue(user.organization_id)


@router.post("/run")
def run_pqc_benchmarks(
    body: BenchmarkRunRequest | None = None,
    user: User = Depends(require_permissions(Permission.RUN_SCANS)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Measure this host now. Classical algorithms always; PQC only when liboqs is installed."""
    body = body or BenchmarkRunRequest()
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A benchmark run is already in progress")
    try:
        result = pqc_benchmarks.run_benchmark(
            _reference(), iterations=body.iterations, include_pqc=body.include_pqc
        )
    finally:
        _run_lock.release()
    _latest_runs[user.organization_id] = result
    record_audit(
        db,
        action="benchmark.run",
        organization_id=user.organization_id,
        user=user,
        metadata={
            "iterations": body.iterations,
            "include_pqc": body.include_pqc,
            "measured": sorted(result["measured"]),
        },
    )
    db.commit()
    return _catalogue(user.organization_id)


@router.get("/migration-impact")
def get_migration_impact(
    kex_from: str = Query("ECDH-P256", description="Current key-exchange algorithm"),
    kex_to: str = Query("ML-KEM-768", description="Target key-exchange algorithm"),
    auth_from: str = Query("RSA-2048", description="Current certificate signature algorithm"),
    auth_to: str = Query("ML-DSA-65", description="Target certificate signature algorithm"),
    chain_certs: int | None = Query(None, ge=1, le=pqc_benchmarks.MAX_CHAIN_CERTS),
    user: User = Depends(require_permissions(Permission.VIEW_DASHBOARD)),
) -> dict[str, Any]:
    """Estimate what a TLS 1.3 handshake costs before and after migrating."""
    try:
        return pqc_benchmarks.migration_impact(
            _reference(), kex_from, kex_to, auth_from, auth_to, chain_certs
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
