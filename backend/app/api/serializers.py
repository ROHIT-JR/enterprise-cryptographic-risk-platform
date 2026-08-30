from backend.app.models import Asset, Project, RiskFinding
from backend.app.schemas.asset import AssetResponse, AssetRiskSummary
from backend.app.schemas.risk import RiskResponse


def serialize_asset(asset: Asset) -> AssetResponse:
    risk = (
        AssetRiskSummary(
            score=asset.risk.score,
            severity=asset.risk.severity,
            reasons=asset.risk.reasons,
        )
        if asset.risk
        else None
    )
    return AssetResponse(
        id=asset.id,
        organization_id=asset.organization_id,
        project_id=asset.project_id,
        project_name=asset.project.name,
        scan_id=asset.scan_id,
        type=asset.asset_type,
        name=asset.name,
        algorithm=asset.algorithm,
        version=asset.version,
        location=asset.location,
        evidence=asset.evidence,
        confidence=asset.confidence,
        dependency_count=asset.dependency_count,
        details=asset.details,
        risk=risk,
        created_at=asset.created_at,
    )


def serialize_risk(risk: RiskFinding, asset: Asset, project: Project) -> RiskResponse:
    return RiskResponse(
        id=risk.id,
        organization_id=risk.organization_id,
        asset_id=asset.id,
        asset_name=asset.name,
        asset_type=asset.asset_type,
        algorithm=asset.algorithm,
        project_id=project.id,
        project_name=project.name,
        score=risk.score,
        severity=risk.severity,
        reasons=risk.reasons,
        factors=risk.factors,
        location=asset.location,
        evidence=asset.evidence,
        created_at=risk.created_at,
    )
