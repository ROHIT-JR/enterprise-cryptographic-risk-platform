from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MoscaVerdict = Literal["critical", "plan", "safe"]


class MoscaSimulateRequest(BaseModel):
    quantum_arrival_year: int = Field(default=2035, ge=2026, le=2060)
    project_id: str | None = None

    model_config = ConfigDict(json_schema_extra={"examples": [{"quantum_arrival_year": 2035}]})


class MoscaAssetResult(BaseModel):
    asset_id: str
    asset_name: str
    algorithm: str | None
    data_lifetime_years: float
    migration_time_years: float
    lhs: float
    verdict: MoscaVerdict


class MoscaSimulateResponse(BaseModel):
    organization_status: MoscaVerdict
    quantum_arrival_year: int
    current_year: int
    years_until_quantum: int
    critical_count: int
    plan_count: int
    safe_count: int
    total_assets: int
    most_urgent_asset: str | None
    formula: str
    items: list[MoscaAssetResult]
