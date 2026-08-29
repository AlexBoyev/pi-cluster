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
    liveness_path: str | None = None
    readiness_path: str | None = None


class WorkloadEnvUpdate(BaseModel):
    env_vars: dict[str, str]


class WorkloadResourceUpdate(BaseModel):
    cpu_limit: str = Field(..., min_length=1)
    memory_limit: str = Field(..., min_length=1)


class WorkloadScale(BaseModel):
    replicas: int = Field(..., ge=1, le=10)


class WorkloadImageUpdate(BaseModel):
    image: str = Field(..., min_length=1)


class WorkloadProbeUpdate(BaseModel):
    liveness_path: str | None = None
    readiness_path: str | None = None


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
    liveness_path: str | None
    readiness_path: str | None
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


class PodInfo(BaseModel):
    name: str
    phase: str
    node: str | None
    pod_ip: str | None
    ready: int
    total: int
    started_at: datetime | None


class NodeCapacity(BaseModel):
    node_name: str
    cpu_allocatable_m: int
    cpu_requested_m: int
    memory_allocatable_mi: int
    memory_requested_mi: int
    ready: bool
    schedulable: bool


class WorkloadMetrics(BaseModel):
    name: str
    cpu_cores: float
    cpu_limit_cores: float
    memory_bytes: int
    memory_limit_bytes: int
    pod_count: int
    available: bool


class DeploymentRevision(BaseModel):
    revision: int
    image: str
    created_at: datetime
    is_current: bool


class WorkloadHistory(BaseModel):
    name: str
    revisions: list[DeploymentRevision]


class RollbackRequest(BaseModel):
    revision: int = Field(..., ge=1)


class HPACreate(BaseModel):
    min_replicas: int = Field(1, ge=1, le=10)
    max_replicas: int = Field(5, ge=1, le=20)
    cpu_target_pct: int = Field(70, ge=10, le=100)


class HPAInfo(BaseModel):
    min_replicas: int | None
    max_replicas: int | None
    cpu_target_pct: int | None
    current_replicas: int | None
    current_cpu_pct: int | None
