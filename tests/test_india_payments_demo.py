from pathlib import Path

from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models import Organization, User
from backend.app.seed import seed_india_payments_demo_org
from scanners.repository import RepositoryScanner

SAMPLE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "sample_enterprise"
    / "india-payments-platform"
)


def test_sample_project_exists_with_all_six_services():
    services = {
        "upi-payment",
        "npci-gateway",
        "aadhaar-auth",
        "imps-neft",
        "mobile-banking-api",
        "core-banking",
    }
    discovered = {path.name for path in (SAMPLE_ROOT / "services").iterdir() if path.is_dir()}
    assert services <= discovered


def test_scanning_the_sample_project_discovers_at_least_40_crypto_assets():
    result = RepositoryScanner().scan_directory(SAMPLE_ROOT, display_name="India Payments Platform")
    crypto_assets = [asset for asset in result.assets if asset.asset_type != "application"]
    assert len(crypto_assets) >= 40
    assert result.metadata["files_scanned"] >= 15


def test_scan_finds_the_headline_algorithms_from_the_demo_script():
    result = RepositoryScanner().scan_directory(SAMPLE_ROOT, display_name="India Payments Platform")
    names = {asset.name for asset in result.assets}
    # These are the exact findings the demo script walks through.
    assert {"RSA-2048", "ECC", "AES-256", "SHA-256", "3DES", "SHA-1", "HMAC"} <= names


def test_scan_finds_the_legacy_3des_in_imps_neft():
    result = RepositoryScanner().scan_directory(SAMPLE_ROOT, display_name="India Payments Platform")
    three_des_findings = [
        asset
        for asset in result.assets
        if asset.name == "3DES" and "imps-neft" in asset.location
    ]
    assert len(three_des_findings) >= 2


def test_seed_india_payments_demo_org_is_idempotent():
    with SessionLocal() as db:
        first = seed_india_payments_demo_org(db)
        second = seed_india_payments_demo_org(db)
        assert first.id == second.id

        organization = db.scalar(
            select(Organization).where(Organization.name == "India Payments Platform")
        )
        assert organization is not None
        assert organization.industry == "Fintech"

        admin = db.scalar(
            select(User).where(
                User.organization_id == organization.id,
                User.username == "india-payments-admin",
            )
        )
        assert admin is not None
        assert admin.role == "administrator"
