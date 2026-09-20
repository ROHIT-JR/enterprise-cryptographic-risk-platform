from __future__ import annotations

from pydantic import BaseModel


class NQMRequirement(BaseModel):
    id: str
    label: str
    complete: bool
    progress: int
    evidence: str


class NQMPhase(BaseModel):
    id: int
    name: str
    years: str
    description: str
    progress: int
    status: str
    requirements: list[NQMRequirement]


class SectorProfile(BaseModel):
    id: str
    name: str
    match_industries: list[str]
    regulator: str
    guidance: str
    priority_assets: list[str]
    recommended_baseline: str


class NQMComplianceReport(BaseModel):
    source: str
    organization_id: str
    organization_name: str
    current_phase: int
    overall_progress: int
    phases: list[NQMPhase]
    sector: SectorProfile
