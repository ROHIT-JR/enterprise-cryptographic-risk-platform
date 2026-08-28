from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

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
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_db
from backend.app.models import Scan
from backend.app.schemas.scan import CBOMResponse, DockerScanRequest, ScanResponse, TLSScanRequest
from backend.app.services.orchestrator import run_scan_job
from backend.app.services.scan_service import create_scan, get_or_create_project
from scanners import ScanSource

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post(
    "/repository",
    response_model=ScanResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def scan_repository(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: str = Form(..., min_length=2, max_length=160),
    criticality: Literal["low", "medium", "high", "critical"] = Form("medium"),
    db: Session = Depends(get_db),
) -> Scan:
    filename = Path(file.filename or "repository.zip").name
    if Path(filename).suffix.lower() != ".zip":
        raise HTTPException(status_code=415, detail="Repository uploads must be ZIP archives")

    project = get_or_create_project(db, name=project_name, criticality=criticality)
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
    return scan


@router.post("/docker", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
def scan_docker(
    payload: DockerScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Scan:
    project = get_or_create_project(db, name=payload.project_name, criticality=payload.criticality)
    scan = create_scan(
        db,
        project=project,
        source_type=ScanSource.DOCKER.value,
        target=payload.image,
    )
    db.commit()
    db.refresh(scan)
    background_tasks.add_task(run_scan_job, scan.id, payload.image)
    return scan


@router.post("/tls", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
def scan_tls(
    payload: TLSScanRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Scan:
    project = get_or_create_project(db, name=payload.project_name, criticality=payload.criticality)
    scan = create_scan(
        db,
        project=project,
        source_type=ScanSource.TLS.value,
        target=payload.endpoint,
    )
    db.commit()
    db.refresh(scan)
    background_tasks.add_task(run_scan_job, scan.id, payload.endpoint)
    return scan


@router.get("", response_model=list[ScanResponse])
def list_scans(
    project_id: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Scan]:
    statement = select(Scan)
    if project_id:
        statement = statement.where(Scan.project_id == project_id)
    return list(db.scalars(statement.order_by(Scan.created_at.desc()).limit(limit)))


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(scan_id: str, db: Session = Depends(get_db)) -> Scan:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}/cbom", response_model=CBOMResponse)
def get_cbom(scan_id: str, db: Session = Depends(get_db)) -> CBOMResponse:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not scan.cbom:
        raise HTTPException(
            status_code=409, detail="CBOM is not available until the scan completes"
        )
    return CBOMResponse(scan_id=scan.id, document=scan.cbom)
