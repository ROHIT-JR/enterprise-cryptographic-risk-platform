from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.enterprise import FullHealthResponse
from backend.app.services.neo4j_service import create_graph_store
from scanners import build_default_registry

router = APIRouter(prefix="/health", tags=["health"])
public_router = APIRouter(tags=["health"])


def _probe_connections(db: Session) -> tuple[dict[str, bool], list[str]]:
    components = {"database": False, "neo4j": False}
    errors: list[str] = []

    try:
        db.execute(text("SELECT 1"))
        components["database"] = True
    except Exception:
        errors.append("PostgreSQL connection failed; verify DATABASE_URL and service health.")

    store = None
    try:
        store = create_graph_store()
        components["neo4j"] = store.health()
        if not components["neo4j"]:
            errors.append("Neo4j connection failed; verify NEO4J_URI and credentials.")
    except Exception:
        errors.append("Neo4j connection failed; verify NEO4J_URI and credentials.")
    finally:
        if store is not None:
            store.close()

    return components, errors


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@public_router.get("/health")
def connection_health(response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    components, errors = _probe_connections(db)
    healthy = all(components.values())
    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    payload: dict[str, Any] = {
        "status": "healthy" if healthy else "unhealthy",
        "database": "connected" if components["database"] else "disconnected",
        "neo4j": "connected" if components["neo4j"] else "disconnected",
    }
    if errors:
        payload["errors"] = errors
    return payload


@public_router.get("/health/full", response_model=FullHealthResponse)
def full_health(response: Response, db: Session = Depends(get_db)) -> FullHealthResponse:
    components, _ = _probe_connections(db)
    try:
        scanners = build_default_registry().available()
        scanner_status = "healthy" if scanners else "unhealthy"
    except Exception:
        scanners = []
        scanner_status = "unhealthy"
    if not components["database"] or scanner_status != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return FullHealthResponse(
        backend="healthy",
        postgres="healthy" if components["database"] else "unhealthy",
        neo4j="healthy" if components["neo4j"] else "degraded",
        scanner_engine=scanner_status,
        scanners=scanners,
    )


@router.get("/ready")
def ready(response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    components, errors = _probe_connections(db)
    if not components["database"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    overall = "ready" if components["database"] else "not-ready"
    if components["database"] and not components["neo4j"]:
        overall = "degraded"
    return {"status": overall, "components": components, "errors": errors}
