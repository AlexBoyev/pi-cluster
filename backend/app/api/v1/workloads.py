from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.database import get_db
from app.repositories.workload_repository import WorkloadRepository
from app.schemas.workload import NodeCapacity, WorkloadCreate, WorkloadResponse
from app.services.k8s_service import K8sService
from app.services.workload_service import WorkloadService

router = APIRouter(prefix="/workloads", tags=["workloads"])


def get_service(db: AsyncSession = Depends(get_db)) -> WorkloadService:
    return WorkloadService(WorkloadRepository(db), K8sService())


@router.get("/capacity", response_model=list[NodeCapacity])
async def get_capacity(service: WorkloadService = Depends(get_service)) -> list[NodeCapacity]:
    return await service.get_node_capacities()


@router.get("/", response_model=list[WorkloadResponse])
async def list_workloads(service: WorkloadService = Depends(get_service)) -> list[WorkloadResponse]:
    return await service.list_workloads()


@router.post("/", response_model=WorkloadResponse, status_code=201)
async def create_workload(
    data: WorkloadCreate,
    service: WorkloadService = Depends(get_service),
    _: None = Depends(require_admin),
) -> WorkloadResponse:
    return await service.create_workload(data)


@router.delete("/{name}", response_model=dict)
async def delete_workload(
    name: str,
    service: WorkloadService = Depends(get_service),
    _: None = Depends(require_admin),
) -> dict:
    await service.delete_workload(name)
    return {"deleted": name}


@router.post("/nodes/{node_name}/cordon", response_model=dict)
async def cordon_node(
    node_name: str,
    service: WorkloadService = Depends(get_service),
    _: None = Depends(require_admin),
) -> dict:
    await service.cordon_node(node_name)
    return {"cordoned": node_name}


@router.delete("/nodes/{node_name}/cordon", response_model=dict)
async def uncordon_node(
    node_name: str,
    service: WorkloadService = Depends(get_service),
    _: None = Depends(require_admin),
) -> dict:
    await service.uncordon_node(node_name)
    return {"uncordoned": node_name}
