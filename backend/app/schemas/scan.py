from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DockerScanRequest(BaseModel):
    image: str = Field(min_length=1, max_length=255, examples=["nginx:1.27-alpine"])
    project_name: str = Field(min_length=2, max_length=160)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"


class TLSScanRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=512, examples=["example.com:443"])
    project_name: str = Field(min_length=2, max_length=160)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"


class RepositoryUrlScanRequest(BaseModel):
    url: str = Field(
        min_length=1,
        max_length=512,
        examples=["https://github.com/ROHIT-JR/enterprise-cryptographic-risk-platform"],
    )
    branch: str | None = Field(default=None, max_length=250)
    project_name: str = Field(min_length=2, max_length=160)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    source_type: str
    target: str
    status: str
    progress: int
    error_message: str | None
    summary: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class CBOMResponse(BaseModel):
    scan_id: str
    document: dict[str, Any]
