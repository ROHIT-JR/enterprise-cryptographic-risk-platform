from fastapi import Response

from backend.app.api import health as health_api
from backend.app.api.dashboard import dashboard
from backend.app.api.health import connection_health, live
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.seed import seed_securebank_demo


def test_health_and_seeded_dashboard_contract():
    with SessionLocal() as db:
        seed_securebank_demo(db)
        body = dashboard(db).model_dump()

    assert live() == {"status": "ok"}
    assert body["metrics"]["total_assets"] >= 15
    assert body["metrics"]["critical_assets"] > 0
    assert body["algorithm_distribution"]


def test_openapi_exposes_phase_one_workflows():
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert "/api/v1/scans/repository" in paths
    assert "/api/v1/scans/docker" in paths
    assert "/api/v1/scans/tls" in paths
    assert "/api/v1/scans/{scan_id}/cbom" in paths
    assert "/api/v1/graph" in paths


def test_connection_health_reports_both_local_datastores(monkeypatch):
    class HealthyGraphStore:
        def health(self) -> bool:
            return True

        def close(self) -> None:
            return None

    monkeypatch.setattr(health_api, "create_graph_store", HealthyGraphStore)
    response = Response()
    with SessionLocal() as db:
        body = connection_health(response, db)

    assert response.status_code == 200
    assert body == {
        "status": "healthy",
        "database": "connected",
        "neo4j": "connected",
    }
