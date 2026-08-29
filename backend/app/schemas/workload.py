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
    env_vars: dict[str, str] = Field(default_factory=dict)
    cpu_limit: str = "500m"
    memory_limit: str = "256Mi"


class WorkloadEnvUpdate(BaseModel):
    env_vars: dict[str, str]


class WorkloadResourceUpdate(BaseModel):
    cpu_limit: str = Field(..., min_length=1)
    memory_limit: str = Field(..., min_length=1)


class WorkloadScale(BaseModel):
    replicas: int = Field(..., ge=1, le=10)


class WorkloadImageUpdate(BaseModel):
    image: str = Field(..., min_length=1)


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
    env_vars: dict[str, str]
    cpu_limit: str
    memory_limit: str
    status: WorkloadStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkloadLogs(BaseModel):
    name: str
    pod_name: str
    logs: str


class WorkloadEvent(BaseModel):
    type: str
    reason: str
    message: str
    object_name: str
    count: int
    first_time: datetime | None
    last_time: datetime | None


class NodeCapacity(BaseModel):
    node_name: str
    cpu_allocatable_m: int
    cpu_requested_m: int
    memory_allocatable_mi: int
    memory_requested_mi: int
    ready: bool
    schedulable: bool
