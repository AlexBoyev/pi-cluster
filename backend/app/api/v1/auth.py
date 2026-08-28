from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessToken, LoginRequest, RefreshRequest, TokenPair, UserInfo

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await UserRepository(db).get_by_username(body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    return TokenPair(
        access_token=create_access_token(user.username, user.role.value),
        refresh_token=create_refresh_token(user.username),
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AccessToken:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise exc
        username: str = payload.get("sub", "")
    except JWTError:
        raise exc

    user = await UserRepository(db).get_by_username(username)
    if user is None or not user.is_active:
        raise exc
    return AccessToken(access_token=create_access_token(user.username, user.role.value))


@router.get("/me", response_model=UserInfo)
async def me(user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(username=user.username, role=user.role.value)
