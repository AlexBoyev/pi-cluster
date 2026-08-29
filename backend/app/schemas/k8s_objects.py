from datetime import datetime

from pydantic import BaseModel


class StatefulSetInfo(BaseModel):
    name: str
    namespace: str
    replicas: int
    ready_replicas: int
    service_name: str | None
    images: list[str]
    created_at: datetime | None


class DaemonSetInfo(BaseModel):
    name: str
    namespace: str
    desired: int
    current: int
    ready: int
    available: int
    images: list[str]
    created_at: datetime | None
