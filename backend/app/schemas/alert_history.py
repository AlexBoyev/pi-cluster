from datetime import datetime

from pydantic import BaseModel


class AlertHistoryEntry(BaseModel):
    id: int
    alert_name: str
    severity: str
    node_name: str | None
    instance: str | None
    summary: str | None
    fired_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}
