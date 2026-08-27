from datetime import datetime

from pydantic import BaseModel

from app.models.node import NodeStatus


class NodeCreate(BaseModel):
    name: str
    ip_address: str


class NodeResponse(BaseModel):
    id: int
    name: str
    ip_address: str
    status: NodeStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
