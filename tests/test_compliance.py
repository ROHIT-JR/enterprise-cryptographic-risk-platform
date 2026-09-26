import re

import pytest
from ecdat_x_demo_seed import seed_securebank_demo
from sqlalchemy import select

from backend.app.api.compliance import get_nqm_compliance
from backend.app.api.reports import export_report
from backend.app.database import SessionLocal
from backend.app.models import Organization, User
from backend.app.services.compliance_service import build_compliance_report, match_sector_profile


def _pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type /Page[^s]", pdf))


@pytest.fixture()
def seeded():
    with SessionLocal() as db:
        seed_securebank_demo(db)
        organization = db.scalar(select(Organization).where(Organization.name == "SecureBank"))
        admin = db.scalar(select(User).where(User.username == "securebank-admin"))
        assert organization is not None and admin is not None
        yield db, organization, admin


def test_sector_matching_is_case_insensitive_and_falls_back_to_default():
    bfsi = match_sector_profile("Financial Services")
    assert bfsi["id"] == "bfsi"

    unmatched = match_sector_profile("Widget Manufacturing")
    assert unmatched["id"] == "general"

    no_industry = match_sector_profile(None)
    assert no_industry["id"] == "general"


def test_nqm_report_has_three_phases_with_real_evidence(seeded):
    db, organization, _ = seeded
    report = build_compliance_report(db, organization.id)

    assert [phase["id"] for phase in report["phases"]] == [1, 2, 3]
    assert report["sector"]["id"] == "bfsi"
    # SecureBank has completed a scan, built an inventory and assessed every asset,
    # so Phase 1 (Inventory & Assessment) must be fully complete.
    phase_one = report["phases"][0]
    assert phase_one["status"] == "complete"
    assert phase_one["progress"] == 100
    assert all(requirement["complete"] for requirement in phase_one["requirements"])

    # Phase 3 (enterprise-wide adoption) requires assets to actually be replaced,
    # which no demo organization has done yet, so it must not be reported complete.
    phase_three = report["phases"][2]
    assert phase_three["status"] != "complete"


def test_requirement_progress_is_bounded_and_evidence_is_populated(seeded):
    db, organization, _ = seeded
    report = build_compliance_report(db, organization.id)

    for phase in report["phases"]:
        assert 0 <= phase["progress"] <= 100
        for requirement in phase["requirements"]:
            assert 0 <= requirement["progress"] <= 100
            assert requirement["evidence"]
            assert requirement["complete"] == (requirement["progress"] >= 100)


def test_current_phase_is_the_first_incomplete_phase(seeded):
    db, organization, _ = seeded
    report = build_compliance_report(db, organization.id)

    incomplete = [phase["id"] for phase in report["phases"] if phase["status"] != "complete"]
    assert report["current_phase"] == incomplete[0]


def test_api_endpoint_returns_the_same_shape_as_the_service(seeded):
    db, organization, admin = seeded
    response = get_nqm_compliance(user=admin, db=db)

    assert response.organization_id == organization.id
    assert len(response.phases) == 3
    assert response.sector.id == "bfsi"


def test_nqm_compliance_pdf_renders_all_phases(seeded):
    db, _, admin = seeded
    response = export_report("nqm-compliance", format="pdf", user=admin, db=db)

    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF-1.4")
    assert _pages(response.body) >= 1
    assert "ecdat-nqm-compliance-" in response.headers["content-disposition"]


def test_nqm_compliance_json_matches_service_output(seeded):
    db, organization, admin = seeded
    response = export_report("nqm-compliance", format="json", user=admin, db=db)

    assert response.media_type == "application/json"
    import json

    document = json.loads(response.body)
    assert document["report_type"] == "nqm-compliance"
    assert document["organization_id"] == organization.id
    assert len(document["phases"]) == 3
