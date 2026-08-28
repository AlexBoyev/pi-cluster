from datetime import datetime

from pydantic import BaseModel

from app.models.node import NodeStatus


class NodeMetrics(BaseModel):
    cpu_load_1m: float
    memory_total_bytes: int
    memory_available_bytes: int
    memory_percent: float
    disk_total_bytes: int
    disk_used_bytes: int
    disk_percent: float
    uptime_seconds: float
    temperature_celsius: float | None


class NodeHealthResponse(BaseModel):
    node_id: int
    node_name: str
    ip_address: str
    status: NodeStatus
    metrics: NodeMetrics | None
    checked_at: datetime
    error: str | None = None
