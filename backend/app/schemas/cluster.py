from pydantic import BaseModel


class NodeCapacityDetail(BaseModel):
    node_name: str
    cpu_allocatable_cores: float
    cpu_requested_cores: float
    cpu_used_cores: float
    memory_allocatable_bytes: int
    memory_requested_bytes: int
    memory_used_bytes: int
    ready: bool
    schedulable: bool


class ClusterCapacity(BaseModel):
    cpu_allocatable_cores: float
    cpu_requested_cores: float
    cpu_used_cores: float
    memory_allocatable_bytes: int
    memory_requested_bytes: int
    memory_used_bytes: int
    nodes: list[NodeCapacityDetail]
