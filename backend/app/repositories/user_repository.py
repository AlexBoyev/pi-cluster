from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_username(self, username: str) -> User | None:
        result = await self._db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self._db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_all(self) -> list[User]:
        result = await self._db.execute(select(User).order_by(User.username))
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._db.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def create(self, username: str, hashed_password: str, role: UserRole = UserRole.VIEWER) -> User:
        user = User(username=username, hashed_password=hashed_password, role=role)
        self._db.add(user)
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def update_role(self, user: User, role: UserRole) -> User:
        user.role = role
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def update_password(self, user: User, hashed_password: str) -> User:
        user.hashed_password = hashed_password
        await self._db.commit()
        await self._db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self._db.delete(user)
        await self._db.commit()
