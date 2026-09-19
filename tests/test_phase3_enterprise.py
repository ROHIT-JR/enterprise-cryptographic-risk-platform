from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.api.assets import list_assets
from backend.app.api.audit import list_audit_logs
from backend.app.api.reports import export_report
from backend.app.auth.passwords import verify_password
from backend.app.auth.permissions import Permission, has_permissions
from backend.app.auth.service import AuthenticationService
from backend.app.auth.tokens import TokenError, decode_token
from backend.app.database import SessionLocal
from backend.app.models import Asset, Organization, Project, Scan, User
from backend.app.schemas.auth import LoginRequest, RegisterRequest
from scanners.base import ScannerPlugin, ScanResult
from scanners.registry import ScannerRegistry

PASSWORD = "Correct-Horse-Battery-2026"


def _register(db, organization: str, username: str):
    return AuthenticationService().register(
        db,
        RegisterRequest(
            organization_name=organization,
            industry="Technology",
            username=username,
            email=f"{username}@example.test",
            password=PASSWORD,
        ),
    )


def test_registration_login_refresh_and_password_hashing():
    with SessionLocal() as db:
        tokens = _register(db, "Crypto Labs", "root-admin")
        assert tokens.user.role == "administrator"
        user = db.scalar(select(User).where(User.username == "root-admin"))
        assert user is not None
        assert user.password_hash != PASSWORD
        assert verify_password(PASSWORD, user.password_hash)

        logged_in = AuthenticationService().login(
            db,
            LoginRequest(
                organization="Crypto Labs", username="root-admin", password=PASSWORD
            ),
        )
        assert decode_token(logged_in.access_token)["org"] == user.organization_id

        refreshed = AuthenticationService().refresh(db, tokens.refresh_token)
        assert refreshed.refresh_token != tokens.refresh_token
        with pytest.raises(HTTPException) as replay:
            AuthenticationService().refresh(db, tokens.refresh_token)
        assert replay.value.status_code == 401

        parts = logged_in.access_token.split(".")
        # Alter the *first* signature char: the last base64url char of a 32-byte HMAC carries
        # only 4 significant bits, so replacing it can leave the decoded signature unchanged.
        flipped = "A" if parts[2][0] != "A" else "B"
        tampered = ".".join([parts[0], parts[1], flipped + parts[2][1:]])
        with pytest.raises(TokenError):
            decode_token(tampered)


def test_rbac_role_matrix_blocks_viewer_from_management():
    assert has_permissions("administrator", {Permission.MANAGE_USERS})
    assert has_permissions("security_analyst", {Permission.ANALYZE_RISKS})
    assert has_permissions("auditor", {Permission.EXPORT_FINDINGS})
    assert has_permissions("viewer", {Permission.VIEW_DASHBOARD})
    assert not has_permissions("viewer", {Permission.MANAGE_USERS})
    assert not has_permissions("auditor", {Permission.RUN_SCANS})


def test_organization_isolation_filters_assets():
    with SessionLocal() as db:
        alpha_tokens = _register(db, "Alpha Org", "alpha-admin")
        beta_tokens = _register(db, "Beta Org", "beta-admin")
        users = {
            user.username: user
            for user in db.scalars(
                select(User).where(User.username.in_(["alpha-admin", "beta-admin"]))
            )
        }
        for username, marker in (("alpha-admin", "alpha"), ("beta-admin", "beta")):
            user = users[username]
            project = Project(
                organization_id=user.organization_id,
                name=f"{marker} project",
                criticality="high",
            )
            db.add(project)
            db.flush()
            scan = Scan(
                organization_id=user.organization_id,
                project_id=project.id,
                source_type="repository",
                target=f"{marker}.zip",
                status="completed",
            )
            db.add(scan)
            db.flush()
            db.add(
                Asset(
                    organization_id=user.organization_id,
                    project_id=project.id,
                    scan_id=scan.id,
                    asset_type="algorithm",
                    name=f"{marker}-RSA",
                    algorithm="RSA-2048",
                    location="test.py:1",
                    evidence="RSA",
                )
            )
        db.commit()

        query = {
            "project_id": None,
            "asset_type": None,
            "severity": None,
            "search": None,
            "page": 1,
            "page_size": 25,
            "db": db,
        }
        alpha = list_assets(user=users["alpha-admin"], **query)
        beta = list_assets(user=users["beta-admin"], **query)
        assert {item.name for item in alpha.items} == {"alpha-RSA"}
        assert {item.name for item in beta.items} == {"beta-RSA"}
        assert alpha_tokens.user.organization_id != beta_tokens.user.organization_id


def test_audit_and_pdf_report_generation():
    with SessionLocal() as db:
        _register(db, "Report Org", "report-admin")
        AuthenticationService().login(
            db,
            LoginRequest(
                organization="Report Org", username="report-admin", password=PASSWORD
            ),
        )
        user = db.scalar(select(User).where(User.username == "report-admin"))
        organization = db.scalar(
            select(Organization).where(Organization.name == "Report Org")
        )
        assert user is not None and organization is not None

        audit = list_audit_logs(limit=100, user=user, db=db)
        assert {item.action for item in audit} >= {"organization.created", "user.login"}

        report = export_report("inventory", format="pdf", user=user, db=db)
        assert report.body.startswith(b"%PDF-1.4")
        assert report.media_type == "application/pdf"


def test_scanner_plugin_contract_and_registry_collision_protection():
    class ExampleScanner(ScannerPlugin):
        source_type = "example"
        name = "Example scanner"
        version = "1.2.3"

        async def scan(self, target: str | Path, **options) -> ScanResult:
            return ScanResult(source=self.source_type, target=str(target))

    registry = ScannerRegistry([ExampleScanner()])
    assert registry.available() == ["example"]
    assert registry.describe()[0]["version"] == "1.2.3"
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ExampleScanner())
