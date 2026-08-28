from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models.user import User
from app.repositories.audit_repository import AuditRepository
from app.repositories.workload_repository import WorkloadRepository
from app.schemas.workload import NodeCapacity, WorkloadCreate, WorkloadEvent, WorkloadImageUpdate, WorkloadLogs, WorkloadResponse, WorkloadScale
from app.services.audit_service import AuditService
from app.services.k8s_service import K8sService
from app.services.workload_service import WorkloadService

router = APIRouter(prefix="/workloads", tags=["workloads"])


def get_service(db: AsyncSession = Depends(get_db)) -> WorkloadService:
    return WorkloadService(
        WorkloadRepository(db),
        K8sService(),
        AuditService(AuditRepository(db)),
    )


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
    admin: User = Depends(require_admin),
) -> WorkloadResponse:
    return await service.create_workload(data, actor=admin.username)


@router.patch("/{name}/image", response_model=WorkloadResponse)
async def update_workload_image(
    name: str,
    data: WorkloadImageUpdate,
    service: WorkloadService = Depends(get_service),
    admin: User = Depends(require_admin),
) -> WorkloadResponse:
    return await service.update_workload_image(name, data.image, actor=admin.username)


@router.get("/{name}/events", response_model=list[WorkloadEvent])
async def get_workload_events(
    name: str,
    service: WorkloadService = Depends(get_service),
    _: None = Depends(get_current_user),
) -> list[WorkloadEvent]:
    return await service.get_workload_events(name)


@router.get("/{name}/logs", response_model=WorkloadLogs)
async def get_workload_logs(
    name: str,
    tail: int = 100,
    service: WorkloadService = Depends(get_service),
    _: None = Depends(get_current_user),
) -> WorkloadLogs:
    return await service.get_workload_logs(name, tail_lines=tail)


@router.patch("/{name}/scale", response_model=WorkloadResponse)
async def scale_workload(
    name: str,
    data: WorkloadScale,
    service: WorkloadService = Depends(get_service),
    admin: User = Depends(require_admin),
) -> WorkloadResponse:
    return await service.scale_workload(name, data.replicas, actor=admin.username)


@router.delete("/{name}", response_model=dict)
async def delete_workload(
    name: str,
    service: WorkloadService = Depends(get_service),
    admin: User = Depends(require_admin),
) -> dict:
    await service.delete_workload(name, actor=admin.username)
    return {"deleted": name}


@router.post("/nodes/{node_name}/cordon", response_model=dict)
async def cordon_node(
    node_name: str,
    service: WorkloadService = Depends(get_service),
    admin: User = Depends(require_admin),
) -> dict:
    await service.cordon_node(node_name, actor=admin.username)
    return {"cordoned": node_name}


@router.delete("/nodes/{node_name}/cordon", response_model=dict)
async def uncordon_node(
    node_name: str,
    service: WorkloadService = Depends(get_service),
    admin: User = Depends(require_admin),
) -> dict:
    await service.uncordon_node(node_name, actor=admin.username)
    return {"uncordoned": node_name}
