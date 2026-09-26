from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2_000)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Payments platform",
                    "description": "Card-processing services and their TLS endpoints",
                    "criticality": "critical",
                }
            ]
        }
    )


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    name: str
    description: str | None
    criticality: str
    created_at: datetime
    updated_at: datetime
