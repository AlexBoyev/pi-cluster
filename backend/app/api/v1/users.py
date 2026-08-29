from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin
from app.auth.service import hash_password
from app.database import get_db
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import PasswordChange, RoleUpdate, UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[UserResponse]:
    return await UserRepository(db).get_all()


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserResponse:
    repo = UserRepository(db)
    if await repo.get_by_username(data.username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    role = UserRole.ADMIN if data.role == "admin" else UserRole.VIEWER
    return await repo.create(
        username=data.username,
        hashed_password=hash_password(data.password),
        role=role,
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == actor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
    role = UserRole.ADMIN if data.role == "admin" else UserRole.VIEWER
    return await repo.update_role(user, role)


@router.patch("/{user_id}/password", response_model=UserResponse)
async def change_user_password(
    user_id: int,
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> UserResponse:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if actor.id != user.id and actor.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change another user's password")
    return await repo.update_password(user, hash_password(data.new_password))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_admin),
) -> None:
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == actor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    await repo.delete(user)
