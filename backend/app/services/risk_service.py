from backend.app.models.asset import Asset
from backend.app.models.project import Project
from backend.app.models.risk import RiskFinding
from risk_engine import RiskEngine, RiskInput


class RiskService:
    def __init__(self, engine: RiskEngine | None = None) -> None:
        self.engine = engine or RiskEngine()

    def assess_asset(self, asset: Asset, project: Project) -> RiskFinding:
        details = {**asset.details, "version": asset.version}
        assessment = self.engine.assess(
            RiskInput(
                name=asset.name,
                algorithm=asset.algorithm,
                asset_type=asset.asset_type,
                dependency_count=asset.dependency_count,
                criticality=project.criticality,
                details=details,
            )
        )
        return RiskFinding(
            project_id=project.id,
            asset_id=asset.id,
            score=assessment.score,
            severity=assessment.severity,
            reasons=assessment.reasons,
            factors=[factor.model_dump() for factor in assessment.factors],
        )
