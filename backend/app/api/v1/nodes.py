from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.node_repository import NodeRepository
from app.schemas.node import NodeCreate, NodeResponse
from app.services.node_service import NodeService

router = APIRouter(prefix="/nodes", tags=["nodes"])


def get_node_service(db: AsyncSession = Depends(get_db)) -> NodeService:
    return NodeService(NodeRepository(db))


@router.get("/", response_model=list[NodeResponse])
async def list_nodes(service: NodeService = Depends(get_node_service)) -> list[NodeResponse]:
    return await service.list_nodes()


@router.get("/{node_id}", response_model=NodeResponse)
async def get_node(node_id: int, service: NodeService = Depends(get_node_service)) -> NodeResponse:
    node = await service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node


@router.post("/", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def register_node(data: NodeCreate, service: NodeService = Depends(get_node_service)) -> NodeResponse:
    return await service.register_node(data)
