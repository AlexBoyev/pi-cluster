from fastapi import APIRouter

from app.schemas.cluster import ClusterCapacity
from app.services.cluster_service import get_cluster_capacity

router = APIRouter(prefix="/cluster", tags=["cluster"])


@router.get("/capacity", response_model=ClusterCapacity)
async def cluster_capacity() -> ClusterCapacity:
    return await get_cluster_capacity()
