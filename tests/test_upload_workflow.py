import asyncio
import tempfile
import zipfile
from pathlib import Path
from typing import BinaryIO

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy import select

from backend.app.api.phase15 import get_project_cbom, get_risk_summary
from backend.app.api.upload import scan_repository
from backend.app.config import get_settings
from backend.app.database import SessionLocal
from backend.app.models import Asset, Project, Scan
from backend.app.services import orchestrator
from scanners.registry import ScannerRegistry
from scanners.source_scanner import SourceCodeScanner


class InlineSourceScanner(SourceCodeScanner):
    async def scan(self, target, **options):
        return self.scan_directory(target, **options)


def _repository_archive() -> BinaryIO:
    stream = tempfile.SpooledTemporaryFile()
    with zipfile.ZipFile(stream, "w") as bundle:
        bundle.writestr(
            "secure-bank/auth.py",
            "from Crypto.PublicKey import RSA\nRSA.generate(2048)\n",
        )
        bundle.writestr("secure-bank/requirements.txt", "pycryptodome==3.20.0\n")
        bundle.writestr(
            "secure-bank/Dockerfile",
            "FROM ubuntu:24.04\nRUN apt-get install -y openssl\n",
        )
    stream.seek(0)
    return stream


def test_repository_upload_to_cbom_risk_and_assets(tmp_path: Path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "scan_storage_path", tmp_path / "scan-storage")
    monkeypatch.setattr(
        orchestrator,
        "build_default_registry",
        lambda **_: ScannerRegistry([InlineSourceScanner()]),
    )
    background_tasks = BackgroundTasks()

    with SessionLocal() as db:
        scan = asyncio.run(
            scan_repository(
                background_tasks,
                UploadFile(file=_repository_archive(), filename="secure-bank.zip"),
                "SecureBank Test",
                "critical",
                db,
            )
        )
        scan_id = scan.id

    asyncio.run(background_tasks())

    with SessionLocal() as db:
        completed = db.get(Scan, scan_id)
        project = db.scalar(select(Project).where(Project.name == "SecureBank Test"))
        assets = list(db.scalars(select(Asset).where(Asset.scan_id == scan_id)))

        assert completed is not None
        assert completed.status == "completed"
        assert completed.progress == 100
        assert project is not None
        assert {"RSA-2048", "PyCryptodome", "OpenSSL"} <= {asset.name for asset in assets}

        cbom = get_project_cbom(project.id, db)
        risk = get_risk_summary(project.id, 10, db)

        assert cbom.scan_id == scan_id
        assert cbom.document["bomFormat"] == "ECDAT-CBOM"
        assert risk.total == len(assets)
        assert risk.highest_risks[0].score >= risk.highest_risks[-1].score
