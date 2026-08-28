from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    name: str
    severity: str
    state: str
    node_name: str | None
    summary: str
    description: str
    fired_at: datetime
    duration_seconds: int
