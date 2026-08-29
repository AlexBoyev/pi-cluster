from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        action: str,
        resource_type: str,
        resource_name: str,
        actor: str,
        status: str,
        detail: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_name=resource_name,
            actor=actor,
            status=status,
            detail=detail,
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def get_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        resource_type: str | None = None,
    ) -> list[AuditLog]:
        q = select(AuditLog).order_by(AuditLog.created_at.desc())
        if status:
            q = q.where(AuditLog.status == status)
        if resource_type:
            q = q.where(AuditLog.resource_type == resource_type)
        result = await self._db.execute(q.offset(offset).limit(limit))
        return list(result.scalars().all())
