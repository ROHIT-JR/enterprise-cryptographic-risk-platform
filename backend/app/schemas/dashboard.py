from pydantic import BaseModel

from backend.app.schemas.common import DistributionItem
from backend.app.schemas.scan import ScanResponse


class DashboardMetrics(BaseModel):
    total_assets: int
    critical_assets: int
    high_assets: int
    algorithms_found: int
    projects_scanned: int


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    risk_distribution: list[DistributionItem]
    algorithm_distribution: list[DistributionItem]
    recent_scans: list[ScanResponse]
