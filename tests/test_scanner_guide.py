"""The scanner guide's example must run: it is the contract new scanners are written against."""

import asyncio
import datetime
import re
import secrets
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID
from sqlalchemy import select

from backend.app.auth.service import AuthenticationService
from backend.app.database import SessionLocal
from backend.app.models import Asset, RiskFinding, Scan
from backend.app.schemas.auth import RegisterRequest
from backend.app.services import orchestrator
from backend.app.services.scan_service import create_scan, get_or_create_project
from scanners.registry import ScannerRegistry, build_default_registry

GUIDE = Path(__file__).resolve().parent.parent / "docs" / "scanner-development.md"


def _guide_example() -> str:
    text = GUIDE.read_text(encoding="utf-8")
    match = re.search(r"<!-- scanner-example -->\s*```python\n(.*?)```", text, re.DOTALL)
    assert match, "docs/scanner-development.md lost its <!-- scanner-example --> block"
    return match.group(1)


@pytest.fixture(scope="module")
def scanner_class():
    namespace: dict = {}
    exec(compile(_guide_example(), str(GUIDE), "exec"), namespace)  # noqa: S102
    return namespace["PemCertificateScanner"]


def _certificate(key, common_name: str) -> bytes:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM)


@pytest.fixture
def certificates(tmp_path):
    (tmp_path / "rsa.pem").write_bytes(
        _certificate(rsa.generate_private_key(public_exponent=65537, key_size=2048), "rsa.example")
    )
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "ec.pem").write_bytes(
        _certificate(ec.generate_private_key(ec.SECP256R1()), "ec.example")
    )
    return tmp_path


def scan(plugin, target):
    return asyncio.run(plugin.scan(target))


# --- the example follows the contract ---------------------------------------------------------
def test_example_reports_each_certificate_with_evidence_and_a_location(scanner_class, certificates):
    result = scan(scanner_class(), certificates)

    by_algorithm = {asset.algorithm: asset for asset in result.assets}
    assert set(by_algorithm) == {"RSA-2048", "ECC secp256r1"}
    rsa_asset = by_algorithm["RSA-2048"]
    assert rsa_asset.asset_type == "certificate"
    assert rsa_asset.name == "CN=rsa.example"
    assert rsa_asset.location == "rsa.pem"
    assert rsa_asset.evidence == "RSA-2048 public key, signed with sha256"
    assert by_algorithm["ECC secp256r1"].location == str(Path("nested") / "ec.pem")
    assert result.source == "pem-directory"
    assert result.warnings == []
    # a finding is identified by type, name, location and evidence, so re-scans line up
    assert (
        result.assets[0].fingerprint()
        == scan(scanner_class(), certificates).assets[0].fingerprint()
    )


def test_example_treats_bad_input_as_a_warning_not_a_crash(scanner_class, tmp_path):
    (tmp_path / "junk.pem").write_text("this is not a certificate")
    (tmp_path / "huge.pem").write_bytes(b"x" * (256 * 1024 + 1))
    (tmp_path / "empty.pem").write_bytes(b"")

    result = scan(scanner_class(), tmp_path)

    assert result.assets == []
    assert sorted(w.split(":")[0] for w in result.warnings) == ["empty.pem", "huge.pem", "junk.pem"]


def test_example_does_not_follow_symlinks(scanner_class, certificates, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside")
    (outside / "secret.pem").write_bytes(
        _certificate(ec.generate_private_key(ec.SECP256R1()), "outside.example")
    )
    try:
        (certificates / "link.pem").symlink_to(outside / "secret.pem")
    except (OSError, NotImplementedError):
        pytest.skip("this platform cannot create symlinks without privileges")

    result = scan(scanner_class(), certificates)

    assert "outside.example" not in " ".join(asset.name for asset in result.assets)
    assert any(w.startswith("link.pem") for w in result.warnings)


def test_example_validates_its_target_before_reading_anything(scanner_class, certificates):
    with pytest.raises(ValueError, match="directory"):
        scan(scanner_class(), certificates / "rsa.pem")  # a file, not a directory
    with pytest.raises(ValueError, match="directory"):
        scan(scanner_class(), certificates / "does-not-exist")


def test_example_bounds_how_many_files_it_reads(scanner_class, tmp_path, monkeypatch):
    plugin = scanner_class()
    monkeypatch.setitem(type(plugin).scan.__globals__, "MAX_FILES", 3)
    for index in range(10):
        (tmp_path / f"{index}.pem").write_text("junk")
    assert len(scan(plugin, tmp_path).warnings) == 3


def test_registry_rejects_a_duplicate_source_type(scanner_class):
    registry = ScannerRegistry([scanner_class()])
    assert registry.available() == ["pem-directory"]
    with pytest.raises(ValueError, match="already registered"):
        registry.register(scanner_class())
    assert registry.describe()[0]["status"] == "healthy"  # the default health() is enough


# --- ...and a scanner registered as the guide says works end to end -----------------------------
def test_a_new_source_type_runs_through_the_real_scan_pipeline(
    scanner_class, certificates, monkeypatch
):
    """Register the example the way the guide says, then run a scan job and read the inventory."""
    with SessionLocal() as db:
        organization_id = (
            AuthenticationService()
            .register(
                db,
                RegisterRequest(
                    organization_name="Pem Org",
                    username="pem-admin",
                    email="pem-admin@example.test",
                    password=secrets.token_urlsafe(24),
                ),
            )
            .user.organization_id
        )
        project = get_or_create_project(
            db, name="Certificates", criticality="high", organization_id=organization_id
        )
        scan_row = create_scan(
            db, project=project, source_type="pem-directory", target=str(certificates)
        )
        db.commit()
        scan_id = scan_row.id

    def registry_with_the_example(**settings):
        registry = build_default_registry(**settings)
        registry.register(
            scanner_class()
        )  # what the guide's step 2 does in build_default_registry()
        return registry

    monkeypatch.setattr(orchestrator, "build_default_registry", registry_with_the_example)
    asyncio.run(orchestrator.run_scan_job(scan_id, str(certificates)))

    with SessionLocal() as db:
        scan_row = db.get(Scan, scan_id)
        assert scan_row.status == "completed", scan_row.error_message
        assert scan_row.summary["assets_discovered"] == 2
        assets = {a.algorithm: a for a in db.scalars(select(Asset).where(Asset.scan_id == scan_id))}
        assert set(assets) == {"RSA-2048", "ECC secp256r1"}
        finding = db.scalar(
            select(RiskFinding).where(RiskFinding.asset_id == assets["RSA-2048"].id)
        )
        # scored like any other scanner's output: an RSA certificate is quantum-vulnerable
        assert finding.severity in {"high", "critical"}
        assert scan_row.cbom["bomFormat"] == "CycloneDX"
