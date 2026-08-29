from datetime import datetime

from pydantic import BaseModel


class ClusterEvent(BaseModel):
    namespace: str
    type: str
    reason: str
    message: str
    object_kind: str
    object_name: str
    count: int
    first_time: datetime | None
    last_time: datetime | None
