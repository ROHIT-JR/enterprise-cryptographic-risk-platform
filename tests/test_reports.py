import json
import re

import pytest
from ecdat_x_demo_seed import seed_securebank_demo
from sqlalchemy import select

from backend.app.api.reports import export_report
from backend.app.database import SessionLocal
from backend.app.models import Organization, User
from backend.app.services.report_service import ReportService, severity_band


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


def test_severity_band_matches_documented_ranges():
    assert [severity_band(score) for score in (0, 30, 31, 60, 61, 80, 81, 100)] == [
        "low",
        "low",
        "medium",
        "medium",
        "high",
        "high",
        "critical",
        "critical",
    ]


def test_executive_summary_reports_the_key_metrics(seeded):
    db, organization, admin = seeded
    summary = ReportService().executive_summary(
        db, organization_id=organization.id, analyst=admin.username
    )

    assert summary["organization_name"] == "SecureBank"
    assert summary["analyst"] == "securebank-admin"
    assert summary["scan_date"] is not None
    assert 0 < summary["risk_score"] <= 100
    assert summary["risk_band"] == severity_band(summary["risk_score"])
    assert summary["metrics"]["critical_findings"] >= 2
    assert summary["metrics"]["total_assets"] >= 19
    assert summary["metrics"]["hndl_at_risk"] >= 1

    top = summary["top_assets"]
    assert len(top) == 5
    assert top[0]["asset"] == "SecureBank RSA-2048 Certificate"
    assert top[0]["score"] == 94
    assert top[0]["dependent_systems"] == 43
    assert [item["score"] for item in top] == sorted((i["score"] for i in top), reverse=True)
    assert sum(summary["severity_counts"].values()) == summary["metrics"]["analyzed_assets"]
    assert summary["recommendation"]


def test_mosca_status_evaluates_the_inequality_with_a_relative_horizon(seeded):
    db, organization, _ = seeded
    mosca = ReportService().executive_summary(db, organization_id=organization.id)["mosca"]

    # 20-year retention on the certificate + ~2 years to migrate, against a ~9 year horizon.
    assert mosca["status"] == "behind"
    assert mosca["data_lifetime_years"] == 20
    assert mosca["migration_years"] == 2
    assert mosca["formula"].startswith("20 + 2 >")
    assert 0 < mosca["years_to_quantum"] < 30


def test_technical_report_has_every_section(seeded):
    db, organization, admin = seeded
    report = ReportService().technical_report(
        db, organization_id=organization.id, analyst=admin.username
    )

    assert {item["type"] for item in report["inventory"]} >= {
        "algorithm",
        "certificate",
        "protocol",
    }
    assert {item["category"] for item in report["risk_by_category"]} >= {"algorithm", "protocol"}
    assert len(report["graph"]["nodes"]) > 40 and report["graph"]["edges"]
    assert [wave["wave"] for wave in report["roadmap"]] == [1, 2, 3]
    matrix = {(row["current"], row["recommended"]) for row in report["pqc_matrix"]}
    assert any("ML-KEM" in recommended for _, recommended in matrix)
    # Dependents collapse into a row per recommendation instead of one row per application.
    assert len(report["pqc_matrix"]) < 12
    assert report["cbom"]["spec_version"] == "1.6"
    json.dumps(report)  # must stay JSON-serialisable for format=json


def test_enterprise_cbom_is_valid_cyclonedx_with_risk_scores(seeded):
    db, organization, _ = seeded
    document = ReportService().cbom(db, organization_id=organization.id)

    assert (document["bomFormat"], document["specVersion"]) == ("CycloneDX", "1.6")
    certificate = next(
        item for item in document["components"] if item["name"] == "SecureBank RSA-2048 Certificate"
    )
    scores = {prop["name"]: prop["value"] for prop in certificate["properties"]}
    assert scores["ecdat:risk-score"] == "94.0"
    assert scores["ecdat:risk-severity"] == "critical"

    cyclonedx = pytest.importorskip("cyclonedx.validation.json")
    from cyclonedx.schema import SchemaVersion

    assert (
        cyclonedx.JsonStrictValidator(SchemaVersion.V1_6).validate_str(json.dumps(document)) is None
    )


def test_executive_summary_pdf_is_a_single_branded_page(seeded):
    db, organization, admin = seeded
    response = export_report("executive-summary", format="pdf", user=admin, db=db)

    assert response.media_type == "application/pdf"
    assert response.body.startswith(b"%PDF-1.4")
    assert _pages(response.body) == 1
    assert "ecdat-executive-summary-" in response.headers["content-disposition"]


def test_technical_pdf_is_multi_page(seeded):
    db, _, admin = seeded
    response = export_report("technical", format="pdf", user=admin, db=db)

    assert response.body.startswith(b"%PDF-1.4")
    assert _pages(response.body) >= 3


@pytest.mark.parametrize("report_type", ["inventory", "quantum-risk", "migration"])
def test_legacy_report_types_now_render_real_documents(seeded, report_type):
    db, _, admin = seeded
    response = export_report(report_type, format="pdf", user=admin, db=db)

    assert response.body.startswith(b"%PDF-1.4")
    assert _pages(response.body) >= 1
    # Rows beyond the old 56-line truncation must still be present in a real table.
    assert len(response.body) > 3000


def test_cbom_json_and_pdf_are_side_by_side_renditions(seeded):
    db, _, admin = seeded
    as_json = export_report("inventory", format="cbom", user=admin, db=db)
    as_pdf = export_report("inventory", format="cbom-pdf", user=admin, db=db)

    document = json.loads(as_json.body)
    assert document["bomFormat"] == "CycloneDX"
    assert as_json.media_type == "application/vnd.cyclonedx+json"
    assert as_json.headers["content-disposition"].endswith('.cdx.json"')
    assert as_pdf.media_type == "application/pdf"
    assert as_pdf.body.startswith(b"%PDF-1.4")


def test_json_format_returns_the_report_data(seeded):
    db, _, admin = seeded
    response = export_report("executive-summary", format="json", user=admin, db=db)

    payload = json.loads(response.body)
    assert payload["report_type"] == "executive-summary"
    assert payload["mosca"]["status"] == "behind"


def test_report_types_are_exposed_in_the_openapi_contract():
    from backend.app.main import app

    schema = app.openapi()["paths"]["/api/v1/reports/{report_type}"]["get"]["parameters"]
    report_type = next(item for item in schema if item["name"] == "report_type")
    fmt = next(item for item in schema if item["name"] == "format")
    assert {"executive-summary", "technical"} <= set(report_type["schema"]["enum"])
    assert set(fmt["schema"]["enum"]) == {"json", "pdf", "cbom", "cbom-pdf"}
