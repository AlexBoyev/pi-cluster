from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_name: str
    actor: str
    status: str
    detail: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
