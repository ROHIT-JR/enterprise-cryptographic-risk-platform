from pydantic import BaseModel, Field


class DistributionItem(BaseModel):
    name: str
    value: int = Field(ge=0)


class MessageResponse(BaseModel):
    message: str
