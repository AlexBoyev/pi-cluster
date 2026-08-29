from datetime import datetime

from pydantic import BaseModel, Field


class NamespaceInfo(BaseModel):
    name: str
    status: str
    created_at: datetime | None
    labels: dict[str, str]


class NamespaceCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]{0,62}$")
