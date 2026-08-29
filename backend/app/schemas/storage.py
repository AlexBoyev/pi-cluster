from datetime import datetime

from pydantic import BaseModel


class PVCInfo(BaseModel):
    name: str
    namespace: str
    status: str
    capacity: str | None
    storage_class: str | None
    access_modes: list[str]
    volume_name: str | None
    created_at: datetime | None


class PVInfo(BaseModel):
    name: str
    status: str
    capacity: str | None
    access_modes: list[str]
    storage_class: str | None
    reclaim_policy: str | None
    claim_namespace: str | None
    claim_name: str | None
    created_at: datetime | None
