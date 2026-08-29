from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_history import AlertHistory


class AlertHistoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_open(self) -> list[AlertHistory]:
        q = select(AlertHistory).where(AlertHistory.resolved_at.is_(None))
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def create_firing(
        self,
        alert_name: str,
        severity: str,
        fired_at: datetime,
        node_name: str | None = None,
        instance: str | None = None,
        summary: str | None = None,
        labels: str | None = None,
    ) -> AlertHistory:
        entry = AlertHistory(
            alert_name=alert_name,
            severity=severity,
            node_name=node_name,
            instance=instance,
            summary=summary,
            labels=labels,
            fired_at=fired_at,
        )
        self._db.add(entry)
        await self._db.commit()
        await self._db.refresh(entry)
        return entry

    async def resolve_firing(self, entry_id: int, resolved_at: datetime) -> None:
        entry = await self._db.get(AlertHistory, entry_id)
        if entry:
            entry.resolved_at = resolved_at
            await self._db.commit()

    async def get_recent(
        self,
        limit: int = 100,
        offset: int = 0,
        severity: str | None = None,
        state: str | None = None,
    ) -> list[AlertHistory]:
        q = select(AlertHistory).order_by(AlertHistory.fired_at.desc())
        if severity:
            q = q.where(AlertHistory.severity == severity)
        if state == "active":
            q = q.where(AlertHistory.resolved_at.is_(None))
        elif state == "resolved":
            q = q.where(AlertHistory.resolved_at.is_not(None))
        result = await self._db.execute(q.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count_active(self) -> int:
        q = select(AlertHistory).where(AlertHistory.resolved_at.is_(None))
        result = await self._db.execute(q)
        return len(result.scalars().all())
