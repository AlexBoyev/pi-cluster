from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_username(self, username: str) -> User | None:
        result = await self._db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self._db.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def create(self, username: str, hashed_password: str, role: UserRole = UserRole.VIEWER) -> User:
        user = User(username=username, hashed_password=hashed_password, role=role)
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user
