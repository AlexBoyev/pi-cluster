from datetime import datetime

from pydantic import BaseModel, Field


class ConfigMapSummary(BaseModel):
    name: str
    namespace: str
    data_keys: list[str]
    created_at: datetime | None


class ConfigMapDetail(BaseModel):
    name: str
    namespace: str
    data: dict[str, str]
    created_at: datetime | None


class ConfigMapCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]{0,62}$")
    namespace: str = "pi-apps"
    data: dict[str, str] = Field(default_factory=dict)


class ConfigMapUpdate(BaseModel):
    data: dict[str, str]
