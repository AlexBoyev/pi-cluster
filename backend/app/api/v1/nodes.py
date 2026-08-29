import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.repositories.node_repository import NodeRepository
from app.schemas.node import NodeCreate, NodeResponse
from app.schemas.node_metrics import NodeMetricsHistory
from app.services.node_metrics_service import get_metrics_history
from app.services.node_service import NodeService

router = APIRouter(prefix="/nodes", tags=["nodes"])


def get_node_service(db: AsyncSession = Depends(get_db)) -> NodeService:
    return NodeService(NodeRepository(db))


@router.get("/", response_model=list[NodeResponse])
async def list_nodes(service: NodeService = Depends(get_node_service)) -> list[NodeResponse]:
    return await service.list_nodes()


@router.post("/all/restart", status_code=202)
async def restart_all_nodes(
    service: NodeService = Depends(get_node_service),
    _: None = Depends(require_admin),
) -> dict:
    nodes = await service.list_nodes()
    from app.services.ssh_service import ssh_service
    await asyncio.gather(
        *[ssh_service.exec_command(n.ip_address, "sudo reboot") for n in nodes],
        return_exceptions=True,
    )
    return {"status": "restarting", "count": len(nodes)}


@router.post("/all/shutdown", status_code=202)
async def shutdown_all_nodes(
    service: NodeService = Depends(get_node_service),
    _: None = Depends(require_admin),
) -> dict:
    nodes = await service.list_nodes()
    from app.services.ssh_service import ssh_service
    await asyncio.gather(
        *[ssh_service.exec_command(n.ip_address, "sudo shutdown -h now") for n in nodes],
        return_exceptions=True,
    )
    return {"status": "shutting_down", "count": len(nodes)}


@router.get("/{node_id}/metrics/history", response_model=NodeMetricsHistory)
async def get_node_metrics_history(
    node_id: int,
    period: str = "1h",
    service: NodeService = Depends(get_node_service),
    _: None = Depends(get_current_user),
) -> NodeMetricsHistory:
    node = await service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if period not in ("1h", "6h", "24h"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period must be 1h, 6h, or 24h")
    return await get_metrics_history(node.name, period)


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: int, service: NodeService = Depends(get_node_service)) -> NodeResponse:
    node = await service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node


@router.post("/{node_id}/restart", status_code=202)
async def restart_node(
    node_id: int,
    service: NodeService = Depends(get_node_service),
    _: None = Depends(require_admin),
) -> dict:
    node = await service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    from app.services.ssh_service import ssh_service
    await ssh_service.exec_command(node.ip_address, "sudo reboot")
    return {"status": "restarting", "node": node.name}


@router.post("/{node_id}/shutdown", status_code=202)
async def shutdown_node(
    node_id: int,
    service: NodeService = Depends(get_node_service),
    _: None = Depends(require_admin),
) -> dict:
    node = await service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")
    from app.services.ssh_service import ssh_service
    await ssh_service.exec_command(node.ip_address, "sudo shutdown -h now")
    return {"status": "shutting_down", "node": node.name}


@router.post("/", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def register_node(data: NodeCreate, service: NodeService = Depends(get_node_service)) -> NodeResponse:
    return await service.register_node(data)
