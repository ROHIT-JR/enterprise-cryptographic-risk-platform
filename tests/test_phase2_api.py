from ecdat_x_demo_seed import seed_securebank_demo
from sqlalchemy import select

from backend.app.api.intelligence import get_blast_radius, get_hndl_analysis, get_intelligence_risk
from backend.app.api.migration import get_recommendations, get_roadmap
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import Asset, BusinessContext, MigrationPlan, RiskAnalysis


def test_phase2_api_contracts_are_exposed():
    paths = app.openapi()["paths"]
    assert "/api/intelligence/risk" in paths
    assert "/api/intelligence/hndl" in paths
    assert "/api/intelligence/blast-radius" in paths
    assert "/api/intelligence/business-context/{asset_id}" in paths
    assert "/api/migration/recommendations" in paths
    assert "/api/migration/roadmap" in paths


def test_securebank_phase2_demo_produces_target_intelligence_and_roadmap():
    with SessionLocal() as db:
        project = seed_securebank_demo(db)
        certificate = db.scalar(
            select(Asset).where(Asset.name == "SecureBank RSA-2048 Certificate")
        )
        assert certificate is not None
        analysis = db.scalar(
            select(RiskAnalysis).where(RiskAnalysis.asset_id == certificate.id)
        )
        context = db.scalar(
            select(BusinessContext).where(BusinessContext.asset_id == certificate.id)
        )

        assert analysis is not None
        assert context is not None
        assert analysis.dependent_systems == 43
        assert analysis.final_score == 94
        assert analysis.evidence_confidence >= 95
        assert analysis.hndl_risk == "critical"
        assert context.data_lifetime_years == 20

        risk = get_intelligence_risk(project.id, db)
        hndl = get_hndl_analysis(project.id, db)
        blast = get_blast_radius(certificate.id, project.id, db)
        recommendations = get_recommendations(project.id, db)
        roadmap = get_roadmap(project.id, db)

        assert risk.metrics.critical_quantum_risks > 0
        assert hndl.total > 0
        assert blast.dependent_systems == 43
        assert len(blast.nodes) == 44
        assert any("ML-KEM" in item.recommended_algorithm for item in recommendations)
        assert [wave.wave for wave in roadmap.waves] == [1, 2, 3]
        assert db.scalar(select(MigrationPlan).where(MigrationPlan.asset_id == certificate.id))
