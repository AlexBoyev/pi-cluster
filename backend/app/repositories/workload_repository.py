from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workload import Workload, WorkloadStatus
from app.schemas.workload import WorkloadCreate


class WorkloadRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_all(self) -> list[Workload]:
        result = await self._db.execute(select(Workload))
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Workload | None:
        result = await self._db.execute(select(Workload).where(Workload.name == name))
        return result.scalar_one_or_none()

    async def create(self, data: WorkloadCreate) -> Workload:
        workload = Workload(
            name=data.name,
            namespace=data.namespace,
            image=data.image,
            replicas=data.replicas,
            target_node=data.target_node,
            container_port=data.container_port,
            ingress_host=data.ingress_host,
        )
        self._db.add(workload)
        await self._db.commit()
        await self._db.refresh(workload)
        return workload

    async def update_status(self, name: str, status: WorkloadStatus) -> Workload | None:
        workload = await self.get_by_name(name)
        if workload is None:
            return None
        workload.status = status
        await self._db.commit()
        await self._db.refresh(workload)
        return workload

    async def update_replicas(self, name: str, replicas: int) -> Workload | None:
        workload = await self.get_by_name(name)
        if workload is None:
            return None
        workload.replicas = replicas
        await self._db.commit()
        await self._db.refresh(workload)
        return workload

    async def update_image(self, name: str, image: str) -> Workload | None:
        workload = await self.get_by_name(name)
        if workload is None:
            return None
        workload.image = image
        await self._db.commit()
        await self._db.refresh(workload)
        return workload

    async def delete(self, name: str) -> bool:
        workload = await self.get_by_name(name)
        if workload is None:
            return False
        await self._db.delete(workload)
        await self._db.commit()
        return True
