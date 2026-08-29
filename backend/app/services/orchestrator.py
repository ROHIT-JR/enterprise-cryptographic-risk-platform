from __future__ import annotations

import logging
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import SessionLocal
from backend.app.models import Asset, AssetRelationship, Project, RiskFinding, Scan
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.services.neo4j_service import create_graph_store
from backend.app.services.risk_service import RiskService
from cbom_engine import CBOMGenerator
from scanners import ScanSource, build_default_registry
from scanners.archive import safe_extract_zip
from scanners.exceptions import ScannerError

logger = logging.getLogger(__name__)


async def run_scan_job(scan_id: str, raw_target: str) -> None:
    """Run a queued scan and persist normalized assets as one recoverable job."""

    settings = get_settings()
    registry = build_default_registry(
        docker_enabled=settings.docker_enabled,
        timeout_seconds=settings.scanner_timeout_seconds,
        tls_timeout_seconds=settings.tls_connect_timeout_seconds,
        tls_allow_private_targets=settings.tls_allow_private_targets,
    )
    db = SessionLocal()
    cleanup_root: Path | None = None
    try:
        scan = db.get(Scan, scan_id)
        if not scan:
            logger.error("Queued scan %s no longer exists", scan_id)
            return
        project = db.get(Project, scan.project_id)
        if not project:
            raise RuntimeError("Scan project no longer exists")

        scan.status = "running"
        scan.progress = 10
        scan.started_at = datetime.now(UTC)
        scan.error_message = None
        db.commit()

        target: str | Path = raw_target
        options: dict[str, Any] = {}
        if scan.source_type == ScanSource.REPOSITORY.value:
            archive = Path(raw_target).resolve()
            cleanup_root = (settings.scan_storage_path / scan.id).resolve()
            if not archive.is_relative_to(cleanup_root):
                raise ScannerError("Repository upload path failed the storage boundary check")
            extracted = cleanup_root / "extracted"
            target = safe_extract_zip(
                archive,
                extracted,
                max_files=settings.max_archive_files,
                max_uncompressed_bytes=settings.max_archive_uncompressed_bytes,
            )
            options["display_name"] = Path(scan.target).stem

        plugin = registry.get(scan.source_type)
        result = await plugin.scan(target, **options)
        scan.progress = 45
        db.commit()

        incoming_dependencies = Counter(
            relationship.target_ref for relationship in result.relationships
        )
        corroborating_evidence = Counter(
            (finding.asset_type, finding.name, finding.algorithm) for finding in result.assets
        )
        rows_by_ref: dict[str, Asset] = {}
        for finding in result.assets:
            row = Asset(
                project_id=project.id,
                scan_id=scan.id,
                asset_type=finding.asset_type,
                name=finding.name,
                algorithm=finding.algorithm,
                version=finding.version,
                location=finding.location,
                evidence=finding.evidence,
                confidence=finding.confidence,
                dependency_count=incoming_dependencies[finding.fingerprint()],
                details={
                    **finding.details,
                    "dependencies": finding.dependencies,
                    "corroborating_evidence_count": corroborating_evidence[
                        (finding.asset_type, finding.name, finding.algorithm)
                    ],
                },
            )
            db.add(row)
            db.flush()
            rows_by_ref[finding.fingerprint()] = row

        relationship_rows: list[AssetRelationship] = []
        seen_edges: set[tuple[str, str, str]] = set()
        for relationship in result.relationships:
            source = rows_by_ref.get(relationship.source_ref)
            target_row = rows_by_ref.get(relationship.target_ref)
            if not source or not target_row or source.id == target_row.id:
                continue
            edge_key = (source.id, target_row.id, relationship.relationship_type)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edge = AssetRelationship(
                project_id=project.id,
                source_asset_id=source.id,
                target_asset_id=target_row.id,
                relationship_type=relationship.relationship_type,
                evidence=relationship.evidence,
            )
            db.add(edge)
            relationship_rows.append(edge)

        scan.progress = 65
        risk_service = RiskService()
        risks: list[RiskFinding] = []
        for asset in rows_by_ref.values():
            risk = risk_service.assess_asset(asset, project)
            db.add(risk)
            risks.append(risk)
        db.flush()

        intelligence = IntelligenceService().analyze_project(db, project)
        scan.progress = 74
        db.flush()

        asset_payloads = [
            _asset_mapping(asset, next((risk for risk in risks if risk.asset_id == asset.id), None))
            for asset in rows_by_ref.values()
        ]
        relationship_payloads = [_relationship_mapping(edge) for edge in relationship_rows]
        cbom = CBOMGenerator().generate(
            project=_project_mapping(project),
            scan=_scan_mapping(scan),
            assets=asset_payloads,
            relationships=relationship_payloads,
        )
        scan.progress = 82

        warnings = list(result.warnings)
        graph_store = create_graph_store(settings)
        try:
            graph_store.sync_scan(
                project=_project_mapping(project),
                scan={**_scan_mapping(scan), "status": "completed"},
                assets=asset_payloads,
                relationships=relationship_payloads,
            )
        except Exception as exc:  # Neo4j is a projection; PostgreSQL remains authoritative.
            logger.warning("Neo4j synchronization failed for scan %s: %s", scan.id, exc)
            warnings.append("Neo4j was unavailable; the graph API will use its PostgreSQL fallback")
        finally:
            graph_store.close()

        severity_counts = Counter(risk.severity for risk in risks)
        type_counts = Counter(asset.asset_type for asset in rows_by_ref.values())
        scan.cbom = cbom
        scan.summary = {
            "assets_discovered": len(rows_by_ref),
            "asset_types": dict(type_counts),
            "risk_severity": dict(severity_counts),
            "quantum_intelligence": {
                "assets_analyzed": len(intelligence),
                "critical_quantum_risks": sum(
                    item.quantum_classification == "critical" for item in intelligence
                ),
                "hndl_exposures": sum(
                    item.hndl_risk in {"critical", "high"} for item in intelligence
                ),
            },
            "warnings": warnings,
            "scanner": result.metadata,
        }
        scan.status = "completed"
        scan.progress = 100
        scan.completed_at = datetime.now(UTC)
        db.commit()
        logger.info(
            "Completed %s scan %s with %d assets", scan.source_type, scan.id, len(rows_by_ref)
        )
    except Exception as exc:
        _mark_failed(db, scan_id, exc)
    finally:
        db.close()
        if cleanup_root:
            _cleanup_scan_upload(cleanup_root, settings.scan_storage_path)


def _mark_failed(db: Session, scan_id: str, exc: Exception) -> None:
    logger.exception("Scan %s failed", scan_id)
    db.rollback()
    scan = db.get(Scan, scan_id)
    if not scan:
        return
    scan.status = "failed"
    scan.error_message = _public_error(exc)
    scan.completed_at = datetime.now(UTC)
    scan.progress = min(scan.progress, 95)
    db.commit()


def _public_error(exc: Exception) -> str:
    if isinstance(exc, ScannerError):
        return str(exc)[:500]
    return "Scan failed due to an internal processing error"


def _cleanup_scan_upload(path: Path, storage_root: Path) -> None:
    try:
        resolved = path.resolve()
        root = storage_root.resolve()
        if resolved.is_relative_to(root) and resolved != root:
            shutil.rmtree(resolved, ignore_errors=True)
    except OSError as exc:
        logger.warning("Unable to clean scan upload %s: %s", path, exc)


def _project_mapping(project: Project) -> dict[str, Any]:
    return {
        "id": project.id,
        "name": project.name,
        "criticality": project.criticality,
    }


def _scan_mapping(scan: Scan) -> dict[str, Any]:
    return {
        "id": scan.id,
        "source_type": scan.source_type,
        "target": scan.target,
        "status": scan.status,
    }


def _asset_mapping(asset: Asset, risk: RiskFinding | None) -> dict[str, Any]:
    return {
        "id": asset.id,
        "asset_type": asset.asset_type,
        "name": asset.name,
        "algorithm": asset.algorithm,
        "version": asset.version,
        "location": asset.location,
        "evidence": asset.evidence,
        "confidence": asset.confidence,
        "risk_score": risk.score if risk else None,
        "risk_severity": risk.severity if risk else None,
    }


def _relationship_mapping(relationship: AssetRelationship) -> dict[str, Any]:
    return {
        "source_asset_id": relationship.source_asset_id,
        "target_asset_id": relationship.target_asset_id,
        "relationship_type": relationship.relationship_type,
        "evidence": relationship.evidence,
    }
