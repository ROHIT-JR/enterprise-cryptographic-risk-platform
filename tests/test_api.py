from backend.app.api.dashboard import dashboard
from backend.app.api.health import live
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
    assert "/api/v1/scans/repository" in paths
    assert "/api/v1/scans/docker" in paths
    assert "/api/v1/scans/tls" in paths
    assert "/api/v1/scans/{scan_id}/cbom" in paths
    assert "/api/v1/graph" in paths
