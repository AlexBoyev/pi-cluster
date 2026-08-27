from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.node import Node, NodeStatus
from app.schemas.node import NodeCreate


class NodeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[Node]:
        result = await self._db.execute(select(Node))
        return list(result.scalars().all())

    async def get_by_id(self, node_id: int) -> Node | None:
        return await self._db.get(Node, node_id)

    async def create(self, data: NodeCreate) -> Node:
        node = Node(**data.model_dump())
        self._db.add(node)
        await self._db.commit()
        await self._db.refresh(node)
        return node

    async def update_status(self, node_id: int, status: NodeStatus) -> Node | None:
        node = await self.get_by_id(node_id)
        if node is None:
            return None
        node.status = status
        await self._db.commit()
        await self._db.refresh(node)
        return node
