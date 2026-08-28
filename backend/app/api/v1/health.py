from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.node_repository import NodeRepository
from app.schemas.health import NodeHealthResponse
from app.services.health_service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


def get_service(db: AsyncSession = Depends(get_db)) -> HealthService:
    return HealthService(NodeRepository(db))


@router.get("/", response_model=list[NodeHealthResponse])
async def get_all_health(service: HealthService = Depends(get_service)) -> list[NodeHealthResponse]:
    """Return latest health for every node (cache hit) or trigger a check (cache miss)."""
    nodes = await service._repo.get_all()
    results = []
    for node in nodes:
        result = await service.get_or_check(node.id)
        if result:
            results.append(result)
    return results


@router.get("/{node_id}", response_model=NodeHealthResponse)
async def get_node_health(node_id: int, service: HealthService = Depends(get_service)) -> NodeHealthResponse:
    result = await service.get_or_check(node_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return result
