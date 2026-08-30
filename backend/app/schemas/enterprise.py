from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None
    action: str
    timestamp: datetime
    metadata: dict[str, Any]


class EnterpriseOverview(BaseModel):
    organizations: int
    users: int
    projects: int
    scans: int
    assets: int
    critical_risks: int
    migration_assets: int
    recent_audit: list[AuditLogResponse]


class FullHealthResponse(BaseModel):
    backend: str
    postgres: str
    neo4j: str
    scanner_engine: str
    scanners: list[str]
