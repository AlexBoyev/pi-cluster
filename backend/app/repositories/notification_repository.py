from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_channel import NotificationChannel


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_all(self) -> list[NotificationChannel]:
        result = await self._db.execute(
            select(NotificationChannel).order_by(NotificationChannel.id)
        )
        return list(result.scalars().all())

    async def list_enabled(self) -> list[NotificationChannel]:
        result = await self._db.execute(
            select(NotificationChannel).where(NotificationChannel.enabled.is_(True))
        )
        return list(result.scalars().all())

    async def get_by_id(self, channel_id: int) -> NotificationChannel | None:
        return await self._db.get(NotificationChannel, channel_id)

    async def create(self, name: str, url: str, enabled: bool = True) -> NotificationChannel:
        ch = NotificationChannel(name=name, url=url, enabled=enabled)
        self._db.add(ch)
        await self._db.commit()
        await self._db.refresh(ch)
        return ch

    async def update(self, ch: NotificationChannel, **kwargs: object) -> NotificationChannel:
        for k, v in kwargs.items():
            setattr(ch, k, v)
        await self._db.commit()
        await self._db.refresh(ch)
        return ch

    async def delete(self, ch: NotificationChannel) -> None:
        await self._db.delete(ch)
        await self._db.commit()
