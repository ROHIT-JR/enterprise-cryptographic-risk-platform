from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth.passwords import hash_password
from backend.app.auth.permissions import Role
from backend.app.config import get_settings
from backend.app.database import SessionLocal, init_db
from backend.app.models import (
    Asset,
    AssetRelationship,
    Organization,
    Project,
    RiskFinding,
    Scan,
    User,
)
from backend.app.services.intelligence_service import IntelligenceService
from backend.app.services.risk_service import RiskService
from cbom_engine import CBOMGenerator

DATA_PATH = Path(__file__).resolve().parents[2] / "sample_data" / "securebank.json"


def seed_securebank_demo(db: Session) -> Project:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    organization = db.scalar(select(Organization).where(Organization.name == "SecureBank"))
    if not organization:
        organization = Organization(name="SecureBank", industry="Financial Services")
        db.add(organization)
        db.flush()
    _ensure_phase3_users(db, organization)
    existing = db.scalar(
        select(Project).where(
            Project.organization_id == organization.id,
            Project.name == "SecureBank Enterprise",
        )
    )
    if existing:
        _ensure_phase2_demo(db, existing, payload)
        _refresh_demo_documents(db, existing)
        db.commit()
        db.refresh(existing)
        return existing

    project = Project(
        organization_id=organization.id,
        name=payload["company"],
        description=payload["description"],
        criticality=payload["criticality"],
    )
    db.add(project)
    db.flush()
    scan = Scan(
        organization_id=organization.id,
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
            "details": application.get("details", {}),
        }
        for asset in application["assets"]:
            definitions[asset["key"]] = asset
        relationship_specs.extend(application["relationships"])

    incoming = Counter(target for _, target, _ in relationship_specs)
    assets_by_key: dict[str, Asset] = {}
    for key, definition in definitions.items():
        asset = Asset(
            organization_id=organization.id,
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
            organization_id=organization.id,
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

    _ensure_phase2_demo(db, project, payload)
    db.flush()

    all_assets = list(db.scalars(select(Asset).where(Asset.project_id == project.id)))
    all_relationships = list(
        db.scalars(
            select(AssetRelationship).where(AssetRelationship.project_id == project.id)
        )
    )
    all_risks = list(db.scalars(select(RiskFinding).where(RiskFinding.project_id == project.id)))
    risk_by_asset = {risk.asset_id: risk for risk in all_risks}
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
        for asset in all_assets
    ]
    relationship_payloads = [
        {
            "source_asset_id": relationship.source_asset_id,
            "target_asset_id": relationship.target_asset_id,
            "relationship_type": relationship.relationship_type,
            "evidence": relationship.evidence,
        }
        for relationship in all_relationships
    ]
    scan.cbom = CBOMGenerator().generate(
        project={"id": project.id, "name": project.name, "criticality": project.criticality},
        scan={"id": scan.id, "source_type": scan.source_type, "target": scan.target},
        assets=asset_payloads,
        relationships=relationship_payloads,
    )
    scan.summary = {
        "assets_discovered": len(all_assets),
        "asset_types": dict(Counter(asset.asset_type for asset in all_assets)),
        "risk_severity": dict(Counter(risk.severity for risk in all_risks)),
        "warnings": [],
        "scanner": {"demo": True, "company": project.name},
    }
    db.commit()
    db.refresh(project)
    return project


def _ensure_phase2_demo(db: Session, project: Project, payload: dict[str, Any]) -> None:
    scan = db.scalar(
        select(Scan).where(Scan.project_id == project.id).order_by(Scan.created_at.desc()).limit(1)
    )
    if not scan:
        return
    payment_certificate = db.scalar(
        select(Asset).where(
            Asset.project_id == project.id,
            Asset.asset_type == "certificate",
            Asset.algorithm.ilike("%RSA%"),
            Asset.location.ilike("%payment%"),
        )
    )
    payment_service = db.scalar(
        select(Asset).where(
            Asset.project_id == project.id,
            Asset.asset_type == "application",
            Asset.name == "Payment Service",
        )
    )
    if not payment_certificate or not payment_service:
        return
    payment_certificate.name = "SecureBank RSA-2048 Certificate"
    payment_certificate.details = {
        **payment_certificate.details,
        "business_criticality": "critical",
        "owner": "Enterprise PKI",
        "data_lifetime_years": 20,
        "data_sensitivity": "financial",
        "evidence_sources": ["source_code", "docker", "tls"],
        "legacy_technology": True,
        "downtime_requirement": "rolling",
        "compatibility": "hybrid-ready",
        "use_case": "key_exchange",
    }
    payment_service.details = {
        **payment_service.details,
        "business_criticality": "critical",
        "owner": "Payments Engineering",
    }

    demo = payload["phase2_demo"]
    expected = int(demo["dependent_services"])
    dependent_assets = [payment_service]
    customer_database = db.scalar(
        select(Asset).where(
            Asset.project_id == project.id,
            Asset.asset_type == "application",
            Asset.name == "Customer Database",
        )
    )
    if not customer_database:
        customer_database = Asset(
            organization_id=project.organization_id,
            project_id=project.id,
            scan_id=scan.id,
            asset_type="application",
            name="Customer Database",
            location="data/customer-records",
            evidence="20-year regulated financial record retention",
            confidence=1.0,
            dependency_count=1,
            details={
                "business_criticality": "critical",
                "owner": "Data Platform",
                "data_lifetime_years": 20,
                "data_sensitivity": "financial",
            },
        )
        db.add(customer_database)
        db.flush()
        _ensure_basic_risk(db, customer_database, project)
    dependent_assets.append(customer_database)

    for index in range(1, expected - 1):
        name = f"Dependent Banking Service {index:02d}"
        application = db.scalar(
            select(Asset).where(
                Asset.project_id == project.id,
                Asset.asset_type == "application",
                Asset.name == name,
            )
        )
        if not application:
            application = Asset(
                organization_id=project.organization_id,
                project_id=project.id,
                scan_id=scan.id,
                asset_type="application",
                name=name,
                location=f"services/dependent-{index:02d}",
                evidence="SecureBank RSA certificate blast-radius simulation",
                confidence=1.0,
                dependency_count=1,
                details={
                    "business_criticality": "high",
                    "owner": "Banking Platform",
                },
            )
            db.add(application)
            db.flush()
            _ensure_basic_risk(db, application, project)
        dependent_assets.append(application)

    existing_edges = {
        (source, target)
        for source, target in db.execute(
            select(
                AssetRelationship.source_asset_id,
                AssetRelationship.target_asset_id,
            ).where(AssetRelationship.project_id == project.id)
        )
    }
    for application in dependent_assets:
        key = (payment_certificate.id, application.id)
        if key in existing_edges:
            continue
        db.add(
            AssetRelationship(
                organization_id=project.organization_id,
                project_id=project.id,
                source_asset_id=payment_certificate.id,
                target_asset_id=application.id,
                relationship_type="PROTECTS",
                evidence="Shared SecureBank enterprise certificate",
            )
        )
    db.flush()
    IntelligenceService().analyze_project(db, project)
    db.flush()


def _ensure_basic_risk(db: Session, asset: Asset, project: Project) -> None:
    existing = db.scalar(select(RiskFinding).where(RiskFinding.asset_id == asset.id))
    if not existing:
        db.add(RiskService().assess_asset(asset, project))


def _refresh_demo_documents(db: Session, project: Project) -> None:
    scan = db.scalar(
        select(Scan).where(Scan.project_id == project.id).order_by(Scan.created_at.desc()).limit(1)
    )
    if not scan:
        return
    assets = list(db.scalars(select(Asset).where(Asset.project_id == project.id)))
    relationships = list(
        db.scalars(
            select(AssetRelationship).where(AssetRelationship.project_id == project.id)
        )
    )
    risks = list(db.scalars(select(RiskFinding).where(RiskFinding.project_id == project.id)))
    risk_by_asset = {risk.asset_id: risk for risk in risks}
    scan.cbom = CBOMGenerator().generate(
        project={"id": project.id, "name": project.name, "criticality": project.criticality},
        scan={"id": scan.id, "source_type": scan.source_type, "target": scan.target},
        assets=[
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
            for asset in assets
        ],
        relationships=[
            {
                "source_asset_id": relationship.source_asset_id,
                "target_asset_id": relationship.target_asset_id,
                "relationship_type": relationship.relationship_type,
                "evidence": relationship.evidence,
            }
            for relationship in relationships
        ],
    )
    scan.summary = {
        "assets_discovered": len(assets),
        "asset_types": dict(Counter(asset.asset_type for asset in assets)),
        "risk_severity": dict(Counter(risk.severity for risk in risks)),
        "warnings": [],
        "scanner": {"demo": True, "company": project.name, "phase": "3"},
    }


def _ensure_phase3_users(db: Session, organization: Organization) -> None:
    password_hash = hash_password(get_settings().demo_password)
    definitions = (
        ("securebank-admin", "admin@securebank.demo", Role.ADMINISTRATOR),
        ("security-analyst", "analyst@securebank.demo", Role.SECURITY_ANALYST),
        ("security-auditor", "auditor@securebank.demo", Role.AUDITOR),
    )
    for username, email, role in definitions:
        user = db.scalar(
            select(User).where(
                User.organization_id == organization.id,
                User.username == username,
            )
        )
        if not user:
            db.add(
                User(
                    organization_id=organization.id,
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    role=role.value,
                )
            )


def main() -> None:
    init_db()
    with SessionLocal() as db:
        project = seed_securebank_demo(db)
        print(f"Seeded demo project: {project.name} ({project.id})")


if __name__ == "__main__":
    main()
