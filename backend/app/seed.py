from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, init_db
from backend.app.models import Asset, AssetRelationship, Project, Scan
from backend.app.services.risk_service import RiskService
from cbom_engine import CBOMGenerator

DATA_PATH = Path(__file__).resolve().parents[2] / "sample_data" / "securebank.json"


def seed_securebank_demo(db: Session) -> Project:
    existing = db.scalar(select(Project).where(Project.name == "SecureBank Enterprise"))
    if existing:
        return existing

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    project = Project(
        name=payload["company"],
        description=payload["description"],
        criticality=payload["criticality"],
    )
    db.add(project)
    db.flush()
    scan = Scan(
        project_id=project.id,
        source_type="repository",
        target="securebank-enterprise-demo.zip",
        status="completed",
        progress=100,
    )
    db.add(scan)
    db.flush()

    definitions: dict[str, dict[str, Any]] = {}
    relationship_specs: list[list[str]] = []
    for application in payload["applications"]:
        definitions[application["key"]] = {
            "key": application["key"],
            "type": "application",
            "name": application["name"],
            "location": application["location"],
            "evidence": "SecureBank enterprise application inventory",
        }
        for asset in application["assets"]:
            definitions[asset["key"]] = asset
        relationship_specs.extend(application["relationships"])

    incoming = Counter(target for _, target, _ in relationship_specs)
    assets_by_key: dict[str, Asset] = {}
    for key, definition in definitions.items():
        asset = Asset(
            project_id=project.id,
            scan_id=scan.id,
            asset_type=definition["type"],
            name=definition["name"],
            algorithm=definition.get("algorithm"),
            version=definition.get("version"),
            location=definition["location"],
            evidence=definition["evidence"],
            confidence=0.99,
            dependency_count=incoming[key],
            details=definition.get("details", {}),
        )
        db.add(asset)
        db.flush()
        assets_by_key[key] = asset

    relationships: list[AssetRelationship] = []
    for source_key, target_key, relationship_type in relationship_specs:
        relationship = AssetRelationship(
            project_id=project.id,
            source_asset_id=assets_by_key[source_key].id,
            target_asset_id=assets_by_key[target_key].id,
            relationship_type=relationship_type,
            evidence="SecureBank reference architecture",
        )
        db.add(relationship)
        relationships.append(relationship)

    risk_service = RiskService()
    risks = []
    for asset in assets_by_key.values():
        risk = risk_service.assess_asset(asset, project)
        db.add(risk)
        risks.append(risk)
    db.flush()

    risk_by_asset = {risk.asset_id: risk for risk in risks}
    asset_payloads = [
        {
            "id": asset.id,
            "asset_type": asset.asset_type,
            "name": asset.name,
            "algorithm": asset.algorithm,
            "version": asset.version,
            "location": asset.location,
            "evidence": asset.evidence,
            "confidence": asset.confidence,
            "risk_score": risk_by_asset[asset.id].score,
            "risk_severity": risk_by_asset[asset.id].severity,
        }
        for asset in assets_by_key.values()
    ]
    relationship_payloads = [
        {
            "source_asset_id": relationship.source_asset_id,
            "target_asset_id": relationship.target_asset_id,
            "relationship_type": relationship.relationship_type,
            "evidence": relationship.evidence,
        }
        for relationship in relationships
    ]
    scan.cbom = CBOMGenerator().generate(
        project={"id": project.id, "name": project.name, "criticality": project.criticality},
        scan={"id": scan.id, "source_type": scan.source_type, "target": scan.target},
        assets=asset_payloads,
        relationships=relationship_payloads,
    )
    scan.summary = {
        "assets_discovered": len(assets_by_key),
        "asset_types": dict(Counter(asset.asset_type for asset in assets_by_key.values())),
        "risk_severity": dict(Counter(risk.severity for risk in risks)),
        "warnings": [],
        "scanner": {"demo": True, "company": project.name},
    }
    db.commit()
    db.refresh(project)
    return project


def main() -> None:
    init_db()
    with SessionLocal() as db:
        project = seed_securebank_demo(db)
        print(f"Seeded demo project: {project.name} ({project.id})")


if __name__ == "__main__":
    main()
