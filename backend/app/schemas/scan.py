from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DockerScanRequest(BaseModel):
    image: str = Field(min_length=1, max_length=255, examples=["nginx:1.27-alpine"])
    project_name: str = Field(min_length=2, max_length=160)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"image": "nginx:1.27-alpine", "project_name": "Edge proxy", "criticality": "high"}
            ]
        }
    )


class TLSScanRequest(BaseModel):
    endpoint: str = Field(min_length=1, max_length=512, examples=["example.com:443"])
    project_name: str = Field(min_length=2, max_length=160)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "endpoint": "portal.securebank.example:443",
                    "project_name": "Customer portal",
                    "criticality": "critical",
                }
            ]
        }
    )


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
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "5d1f3a52-8c4e-4b0a-a3f1-2c9e7d6b1a40",
                    "organization_id": "7c2d9a54-3b1e-4f60-8a37-5e9d1c0b4a22",
                    "project_id": "a9b8c7d6-1234-4e5f-8a9b-0c1d2e3f4a5b",
                    "source_type": "repository",
                    "target": "securebank.zip",
                    "status": "completed",
                    "progress": 100,
                    "error_message": None,
                    "summary": {
                        "assets_discovered": 65,
                        "asset_types": {"algorithm": 9, "library": 4, "application": 46},
                        "risk_severity": {"critical": 2, "high": 6, "medium": 8, "low": 49},
                        "quantum_intelligence": {
                            "assets_analyzed": 65,
                            "critical_quantum_risks": 2,
                            "hndl_exposures": 5,
                        },
                        "warnings": [],
                    },
                    "started_at": "2026-09-01T09:31:02Z",
                    "completed_at": "2026-09-01T09:31:19Z",
                    "created_at": "2026-09-01T09:31:00Z",
                }
            ]
        },
    )

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
