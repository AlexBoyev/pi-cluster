from app.models.node import NodeStatus
from app.repositories.node_repository import NodeRepository
from app.schemas.node import NodeCreate, NodeResponse


class NodeService:
    def __init__(self, repo: NodeRepository) -> None:
        self._repo = repo

    async def list_nodes(self) -> list[NodeResponse]:
        nodes = await self._repo.get_all()
        return [NodeResponse.model_validate(n) for n in nodes]

    async def get_node(self, node_id: int) -> NodeResponse | None:
        node = await self._repo.get_by_id(node_id)
        return NodeResponse.model_validate(node) if node else None

    async def register_node(self, data: NodeCreate) -> NodeResponse:
        node = await self._repo.create(data)
        return NodeResponse.model_validate(node)

    async def set_status(self, node_id: int, status: NodeStatus) -> NodeResponse | None:
        node = await self._repo.update_status(node_id, status)
        return NodeResponse.model_validate(node) if node else None
