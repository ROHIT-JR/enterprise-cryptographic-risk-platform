import asyncio
import tempfile
import zipfile
from typing import BinaryIO

from fastapi import BackgroundTasks, UploadFile

from backend.app.api.upload import scan_repository
from backend.app.config import get_settings
from backend.app.database import SessionLocal
from backend.app.services import orchestrator
from backend.app.services.scan_events import publish, subscribe, unsubscribe
from scanners.registry import ScannerRegistry
from scanners.source_scanner import SourceCodeScanner


class InlineSourceScanner(SourceCodeScanner):
    async def scan(self, target, **options):
        return self.scan_directory(target, **options)


def _repository_archive() -> BinaryIO:
    stream = tempfile.SpooledTemporaryFile()  # noqa: SIM115 - returned to the caller
    with zipfile.ZipFile(stream, "w") as bundle:
        bundle.writestr(
            "demo/auth.py",
            "from Crypto.PublicKey import RSA\nRSA.generate(2048)\n",
        )
        bundle.writestr("demo/requirements.txt", "pycryptodome==3.20.0\n")
    stream.seek(0)
    return stream


def test_subscribe_publish_unsubscribe_round_trip():
    queue = subscribe("scan-xyz")
    publish("scan-xyz", {"type": "stage", "message": "hello"})
    event = queue.get_nowait()
    assert event["type"] == "stage"
    assert event["message"] == "hello"
    assert "ts" in event
    unsubscribe("scan-xyz", queue)


def test_publish_with_no_subscribers_does_not_raise():
    publish("scan-with-nobody-listening", {"type": "stage", "message": "noop"})


def test_full_scan_emits_asset_and_completion_events(tmp_path, monkeypatch):
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
                UploadFile(file=_repository_archive(), filename="demo.zip"),
                "Progress Test Project",
                "medium",
                db,
            )
        )
        scan_id = scan.id

    queue = subscribe(scan_id)
    try:
        asyncio.run(background_tasks())

        events = []
        while not queue.empty():
            events.append(queue.get_nowait())

        assert any(event["type"] == "stage" for event in events)
        asset_events = [event for event in events if event["type"] == "asset"]
        assert any("RSA-2048" in event["message"] for event in asset_events)
        completed = [event for event in events if event["type"] == "completed"]
        assert len(completed) == 1
        assert completed[0]["assets_discovered"] >= 1
        assert "assets discovered" in completed[0]["message"]
    finally:
        unsubscribe(scan_id, queue)
