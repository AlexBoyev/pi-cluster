from datetime import datetime

from pydantic import BaseModel, Field


class SecretSummary(BaseModel):
    name: str
    namespace: str
    type: str
    data_keys: list[str]
    created_at: datetime | None


class SecretDetail(BaseModel):
    name: str
    namespace: str
    type: str
    data: dict[str, str]
    created_at: datetime | None


class SecretCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]{0,62}$")
    namespace: str = "pi-apps"
    type: str = "Opaque"
    data: dict[str, str] = Field(default_factory=dict)


class SecretUpdate(BaseModel):
    data: dict[str, str]
