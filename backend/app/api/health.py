from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.neo4j_service import create_graph_store

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    components = {"database": False, "neo4j": False}
    try:
        db.execute(text("SELECT 1"))
        components["database"] = True
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    store = create_graph_store()
    try:
        components["neo4j"] = store.health()
    finally:
        store.close()
    overall = "ready" if components["database"] else "not-ready"
    if components["database"] and not components["neo4j"]:
        overall = "degraded"
    return {"status": overall, "components": components}
