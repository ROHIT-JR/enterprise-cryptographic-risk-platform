from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Asset, MigrationPlan, Project, RiskAnalysis, Scan

ReportType = Literal["inventory", "quantum-risk", "migration"]


class ReportService:
    def build(
        self,
        db: Session,
        *,
        organization_id: str,
        report_type: ReportType,
    ) -> dict[str, Any]:
        projects = list(
            db.scalars(select(Project).where(Project.organization_id == organization_id))
        )
        header = {
            "report_type": report_type,
            "organization_id": organization_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "project_count": len(projects),
        }
        if report_type == "inventory":
            assets = list(
                db.scalars(
                    select(Asset)
                    .where(Asset.organization_id == organization_id)
                    .order_by(Asset.asset_type, Asset.name)
                )
            )
            return {
                **header,
                "assets": [
                    {
                        "id": asset.id,
                        "type": asset.asset_type,
                        "name": asset.name,
                        "algorithm": asset.algorithm,
                        "version": asset.version,
                        "location": asset.location,
                        "confidence": asset.confidence,
                    }
                    for asset in assets
                ],
            }
        if report_type == "quantum-risk":
            rows = db.execute(
                select(RiskAnalysis, Asset)
                .join(Asset, RiskAnalysis.asset_id == Asset.id)
                .where(RiskAnalysis.organization_id == organization_id)
                .order_by(RiskAnalysis.final_score.desc())
            ).all()
            return {
                **header,
                "risks": [
                    {
                        "asset_id": asset.id,
                        "asset": asset.name,
                        "algorithm": asset.algorithm,
                        "score": risk.final_score,
                        "severity": risk.severity,
                        "hndl_risk": risk.hndl_risk,
                        "dependent_systems": risk.dependent_systems,
                        "explanations": risk.explanations,
                    }
                    for risk, asset in rows
                ],
            }
        rows = db.execute(
            select(MigrationPlan, Asset)
            .join(Asset, MigrationPlan.asset_id == Asset.id)
            .where(MigrationPlan.organization_id == organization_id)
            .order_by(MigrationPlan.wave, Asset.name)
        ).all()
        return {
            **header,
            "migration_plan": [
                {
                    "asset_id": asset.id,
                    "asset": asset.name,
                    "current_algorithm": asset.algorithm or asset.name,
                    "recommended_algorithm": plan.recommended_algorithm,
                    "wave": plan.wave,
                    "complexity": plan.complexity,
                    "reasons": plan.reasons,
                }
                for plan, asset in rows
            ],
        }

    def cbom(self, db: Session, *, organization_id: str) -> dict[str, Any]:
        scans = list(
            db.scalars(
                select(Scan)
                .where(Scan.organization_id == organization_id, Scan.cbom != {})
                .order_by(Scan.created_at.desc())
            )
        )
        return {
            "bomFormat": "ECDAT-X-ENTERPRISE-CBOM",
            "specVersion": "1.0",
            "organization_id": organization_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "documents": [scan.cbom for scan in scans],
        }

    @staticmethod
    def json_bytes(report: dict[str, Any]) -> bytes:
        return json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8")

    @staticmethod
    def pdf_bytes(report: dict[str, Any]) -> bytes:
        lines = [
            "ECDAT-X Enterprise Security Report",
            f"Type: {report['report_type']}",
            f"Generated: {report['generated_at']}",
            f"Organization: {report['organization_id']}",
            "",
        ]
        section = (
            "assets"
            if "assets" in report
            else "risks"
            if "risks" in report
            else "migration_plan"
        )
        for item in report.get(section, [])[:80]:
            summary = " | ".join(
                f"{key}: {value}"
                for key, value in item.items()
                if key != "explanations"
            )
            lines.append(summary[:150])
        return _minimal_pdf(lines)


def _minimal_pdf(lines: list[str]) -> bytes:
    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    content = ["BT", "/F1 10 Tf", "50 790 Td", "13 TL"]
    for line in lines[:56]:
        content.append(f"({escape(line)}) Tj")
        content.append("T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)
