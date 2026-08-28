from datetime import datetime

from pydantic import BaseModel, Field

from app.models.workload import WorkloadStatus


class WorkloadCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z][a-z0-9-]{0,62}$")
    image: str
    replicas: int = Field(1, ge=1, le=10)
    namespace: str = "pi-apps"
    target_node: str | None = None
    cpu_request: str = "100m"
    memory_request: str = "128Mi"
    container_port: int | None = Field(None, ge=1, le=65535)
    ingress_host: str | None = None


class WorkloadResponse(BaseModel):
    id: int
    name: str
    namespace: str
    image: str
    replicas: int
    ready_replicas: int
    target_node: str | None
    container_port: int | None
    ingress_host: str | None
    status: WorkloadStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class NodeCapacity(BaseModel):
    node_name: str
    cpu_allocatable_m: int
    cpu_requested_m: int
    memory_allocatable_mi: int
    memory_requested_mi: int
    ready: bool
    schedulable: bool
