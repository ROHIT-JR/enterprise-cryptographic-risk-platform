from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.app.schemas.common import DistributionItem


class RiskResponse(BaseModel):
    id: str
    asset_id: str
    asset_name: str
    asset_type: str
    algorithm: str | None
    project_id: str
    project_name: str
    score: float
    severity: str
    reasons: list[str]
    factors: list[dict[str, Any]]
    location: str
    evidence: str
    created_at: datetime


class RiskPage(BaseModel):
    items: list[RiskResponse]
    total: int
    page: int
    page_size: int


class RiskSummaryResponse(BaseModel):
    total: int
    severity_distribution: list[DistributionItem]
    highest_risks: list[RiskResponse]
