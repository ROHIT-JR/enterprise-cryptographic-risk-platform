from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, require_permissions
from backend.app.auth.permissions import Permission
from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models import Scan, User
from backend.app.schemas.scan import (
    CBOMResponse,
    DockerScanRequest,
    RepositoryUrlScanRequest,
    ScanResponse,
    TLSScanRequest,
)
from backend.app.services.audit_service import record_audit
from backend.app.services.github_fetch import (
    InvalidRepositoryUrlError,
    download_github_archive,
    parse_github_repo_url,
)
from backend.app.services.orchestrator import run_scan_job
from backend.app.services.scan_events import subscribe, unsubscribe
from backend.app.services.scan_service import create_scan, get_or_create_project
from backend.app.services.tenant_service import resolve_organization_id
from scanners import ScanSource

router = APIRouter(prefix="/scans", tags=["Discovery"])


@router.post(
    "/repository",
    response_model=ScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permissions(Permission.RUN_SCANS))],
)
async def scan_repository(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form(..., min_length=2, max_length=160),
    criticality: Literal["low", "medium", "high", "critical"] = Form("medium"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scan:
    """Upload a ZIP archive of a repository and start a discovery scan.

    Returns `202` with a queued scan; the archive is analyzed in the background. Follow
    `GET /scans/{scan_id}/stream` for live progress, or poll `GET /scans/{scan_id}` until the
    status is `completed` or `failed`. Uploads must be ZIP archives and are limited by
    `ECDAT_MAX_UPLOAD_BYTES` (50 MiB by default).
    """
    filename = Path(file.filename or "repository.zip").name
    if Path(filename).suffix.lower() != ".zip":
        raise HTTPException(status_code=415, detail="Repository uploads must be ZIP archives")

    organization_id = resolve_organization_id(db, user)
    project = get_or_create_project(
        db,
        name=project_name,
        criticality=criticality,
        organization_id=organization_id,
    )
    scan = create_scan(
        db,
        project=project,
        source_type=ScanSource.REPOSITORY.value,
        target=filename,
    )
    db.commit()
    db.refresh(scan)

    settings = get_settings()
    job_directory = (settings.scan_storage_path / scan.id).resolve()
    archive_path = job_directory / "repository.zip"
    job_directory.mkdir(parents=True, exist_ok=False)
    try:
        written = 0
        with archive_path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                written += len(chunk)
                if written > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Upload exceeds {settings.max_upload_bytes // (1024 * 1024)} MiB",
                    )
                destination.write(chunk)
    except Exception:
        shutil.rmtree(job_directory, ignore_errors=True)
        scan.status = "failed"
        scan.error_message = "Repository upload could not be accepted"
        db.commit()
        raise
    finally:
        await file.close()

    background_tasks.add_task(run_scan_job, scan.id, str(archive_path))
    record_audit(
        db,
        action="repository.uploaded",
        organization_id=organization_id,
        user=user if isinstance(user, User) else None,
        metadata={"scan_id": scan.id, "filename": filename},
    )
    db.commit()
    return scan


@router.post(
    "/repository-url",
    response_model=ScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permissions(Permission.RUN_SCANS))],
)
async def scan_repository_url(
    payload: RepositoryUrlScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scan:
    """Fetch a public GitHub repository by URL and start a discovery scan.

    Downloads the repository's zip archive from `codeload.github.com` (the same source
    `git clone` and GitHub's own "Download ZIP" button use) and runs it through the same
    scan pipeline as an uploaded archive. Only `github.com` URLs are accepted; returns `202`
    with a queued scan — follow `GET /scans/{scan_id}/stream` or poll `GET /scans/{scan_id}`
    for progress, same as the upload endpoint.
    """
    try:
        owner, repo = parse_github_repo_url(payload.url)
    except InvalidRepositoryUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    organization_id = resolve_organization_id(db, user)
    project = get_or_create_project(
        db,
        name=payload.project_name,
        criticality=payload.criticality,
        organization_id=organization_id,
    )
    scan = create_scan(
        db,
        project=project,
        source_type=ScanSource.REPOSITORY.value,
        target=f"{owner}/{repo}",
    )
    db.commit()
    db.refresh(scan)

    settings = get_settings()
    job_directory = (settings.scan_storage_path / scan.id).resolve()
    archive_path = job_directory / "repository.zip"
    job_directory.mkdir(parents=True, exist_ok=False)
    try:
        branch_used = await download_github_archive(
            owner, repo, payload.branch, archive_path, settings.max_upload_bytes
        )
    except InvalidRepositoryUrlError as exc:
        shutil.rmtree(job_directory, ignore_errors=True)
        scan.status = "failed"
        scan.error_message = str(exc)
        db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        shutil.rmtree(job_directory, ignore_errors=True)
        scan.status = "failed"
        scan.error_message = "Repository download could not be completed"
        db.commit()
        raise

    background_tasks.add_task(run_scan_job, scan.id, str(archive_path))
    record_audit(
        db,
        action="repository.fetched",
        organization_id=organization_id,
        user=user if isinstance(user, User) else None,
        metadata={"scan_id": scan.id, "url": payload.url, "branch": branch_used},
    )
    db.commit()
    return scan


@router.post(
    "/docker",
    response_model=ScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permissions(Permission.RUN_SCANS))],
)
def scan_docker(
    payload: DockerScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scan:
    """Start a discovery scan of a container image.

    Returns `202` with a queued scan. The image is inspected in the background; follow
    `GET /scans/{scan_id}/stream` or poll `GET /scans/{scan_id}` for progress. Requires the
    Docker plugin (`ECDAT_DOCKER_ENABLED`).
    """
    organization_id = resolve_organization_id(db, user)
    project = get_or_create_project(
        db,
        name=payload.project_name,
        criticality=payload.criticality,
        organization_id=organization_id,
    )
    scan = create_scan(
        db,
        project=project,
        source_type=ScanSource.DOCKER.value,
        target=payload.image,
    )
    db.commit()
    db.refresh(scan)
    background_tasks.add_task(run_scan_job, scan.id, payload.image)
    record_audit(
        db,
        action="scan.started",
        organization_id=organization_id,
        user=user if isinstance(user, User) else None,
        metadata={"scan_id": scan.id, "source_type": "docker"},
    )
    db.commit()
    return scan


@router.post(
    "/tls",
    response_model=ScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permissions(Permission.RUN_SCANS))],
)
def scan_tls(
    payload: TLSScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Scan:
    """Start a discovery scan of a TLS endpoint.

    Returns `202` with a queued scan. The handshake is performed in the background; follow
    `GET /scans/{scan_id}/stream` or poll `GET /scans/{scan_id}` for progress. Private and
    loopback destinations are rejected unless `ECDAT_TLS_ALLOW_PRIVATE_TARGETS` is enabled.
    """
    organization_id = resolve_organization_id(db, user)
    project = get_or_create_project(
        db,
        name=payload.project_name,
        criticality=payload.criticality,
        organization_id=organization_id,
    )
    scan = create_scan(
        db,
        project=project,
        source_type=ScanSource.TLS.value,
        target=payload.endpoint,
    )
    db.commit()
    db.refresh(scan)
    background_tasks.add_task(run_scan_job, scan.id, payload.endpoint)
    record_audit(
        db,
        action="scan.started",
        organization_id=organization_id,
        user=user if isinstance(user, User) else None,
        metadata={"scan_id": scan.id, "source_type": "tls"},
    )
    db.commit()
    return scan


@router.get("", response_model=list[ScanResponse])
def list_scans(
    project_id: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(Permission.VIEW_SCANS)),
) -> list[Scan]:
    """List this organization's scans, newest first, optionally filtered by project."""
    statement = select(Scan)
    if isinstance(user, User):
        statement = statement.where(Scan.organization_id == user.organization_id)
    if project_id:
        statement = statement.where(Scan.project_id == project_id)
    return list(db.scalars(statement.order_by(Scan.created_at.desc()).limit(limit)))


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(Permission.VIEW_SCANS)),
) -> Scan:
    """Return one scan with its status, progress and summary.

    A scan moves `queued` → `running` → `completed` or `failed`, and `progress` climbs from 0 to
    100. Poll this after starting a scan, or use `GET /scans/{scan_id}/stream` to be pushed each
    stage as it happens.
    """
    scan = db.get(Scan, scan_id)
    if not scan or (isinstance(user, User) and scan.organization_id != user.organization_id):
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/{scan_id}/stream")
async def stream_scan_progress(
    scan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(Permission.VIEW_SCANS)),
) -> StreamingResponse:
    """Live scan progress as Server-Sent Events.

    Each event is a JSON payload: ``{"type": "stage" | "asset" | "completed"
    | "failed", "message": str, "progress"?: int}``. The stream closes after
    a terminal ``completed``/``failed`` event.
    """
    scan = db.get(Scan, scan_id)
    if not scan or (isinstance(user, User) and scan.organization_id != user.organization_id):
        raise HTTPException(status_code=404, detail="Scan not found")

    async def event_stream():
        # A client connecting after the scan already progressed (or finished)
        # should see its current state immediately rather than a blank feed.
        yield _sse_event(
            {"type": "stage", "progress": scan.progress, "message": f"Status: {scan.status}"}
        )
        if scan.status in {"completed", "failed"}:
            yield _sse_event(
                {
                    "type": scan.status,
                    "progress": scan.progress,
                    "message": scan.error_message or "Scan already finished",
                }
            )
            return

        queue = subscribe(scan_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield _sse_event(event)
                if event.get("type") in {"completed", "failed"}:
                    break
        finally:
            unsubscribe(scan_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{scan_id}/cbom", response_model=CBOMResponse)
def get_cbom(
    scan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permissions(Permission.VIEW_SCANS)),
) -> CBOMResponse:
    """Return the cryptographic bill of materials produced by a completed scan.

    Returns `409` while the scan is still running, because the CBOM is written when it completes.
    """
    scan = db.get(Scan, scan_id)
    if not scan or (isinstance(user, User) and scan.organization_id != user.organization_id):
        raise HTTPException(status_code=404, detail="Scan not found")
    if not scan.cbom:
        raise HTTPException(
            status_code=409, detail="CBOM is not available until the scan completes"
        )
    return CBOMResponse(scan_id=scan.id, document=scan.cbom)
