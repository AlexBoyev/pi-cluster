from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.known_login_ip import KnownLoginIp


class KnownLoginIpRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def is_known(self, user_id: int, ip_address: str) -> bool:
        result = await self._db.execute(
            select(KnownLoginIp).where(
                KnownLoginIp.user_id == user_id, KnownLoginIp.ip_address == ip_address
            )
        )
        return result.scalar_one_or_none() is not None

    async def record(self, user_id: int, ip_address: str) -> None:
        """Insert if new, bump last_seen if already known. Called after
        is_known() already decided whether this is a new-IP event - this
        just persists the observation either way."""
        result = await self._db.execute(
            select(KnownLoginIp).where(
                KnownLoginIp.user_id == user_id, KnownLoginIp.ip_address == ip_address
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.last_seen = datetime.now(timezone.utc)
        else:
            self._db.add(KnownLoginIp(user_id=user_id, ip_address=ip_address))
        await self._db.commit()
