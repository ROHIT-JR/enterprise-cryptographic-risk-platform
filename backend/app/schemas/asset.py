from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AssetRiskSummary(BaseModel):
    score: float
    severity: str
    reasons: list[str]


class AssetResponse(BaseModel):
    id: str
    project_id: str
    project_name: str
    scan_id: str
    type: str
    name: str
    algorithm: str | None
    version: str | None
    location: str
    evidence: str
    confidence: float
    dependency_count: int
    details: dict[str, Any]
    risk: AssetRiskSummary | None
    created_at: datetime


class AssetPage(BaseModel):
    items: list[AssetResponse]
    total: int
    page: int
    page_size: int
