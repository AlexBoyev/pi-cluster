from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    create_sso_token,
    decode_token,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.rate_limit import limiter
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessToken, LoginRequest, RefreshRequest, TokenPair, UserInfo
from app.services.wallabag_bridge_service import WallabagBridgeService

router = APIRouter(prefix="/auth", tags=["auth"])


async def _sso_user(request: Request, db: AsyncSession) -> User | None:
    """Shared by /verify (nginx auth_request) and /wallabag-sso (the login
    bridge) - both need the same "is there a valid pi-cluster session"
    check, just do different things once they have the answer."""
    token = request.cookies.get(settings.sso_cookie_name)
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "sso":
            return None
        username: str = payload.get("sub", "")
    except JWTError:
        return None
    user = await UserRepository(db).get_by_username(username)
    if user is None or not user.is_active:
        return None
    return user


def _platform_root(request: Request) -> str:
    host = request.headers.get("host", "")
    return "pi.cluster.download" if host.endswith(".cluster.download") else "pi-cluster.lan"


def _set_sso_cookie(response: Response, username: str) -> None:
    token = create_sso_token(username)
    for domain in settings.sso_cookie_domains:
        response.set_cookie(
            key=settings.sso_cookie_name,
            value=token,
            domain=domain,
            path="/",
            max_age=settings.jwt_refresh_token_expire_days * 86400,
            httponly=True,
            samesite="lax",
        )


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(
    request: Request, body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    user = await UserRepository(db).get_by_username(body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
    _set_sso_cookie(response, user.username)
    return TokenPair(
        access_token=create_access_token(user.username, user.role.value),
        refresh_token=create_refresh_token(user.username),
    )


@router.post("/logout")
async def logout(response: Response) -> dict:
    for domain in settings.sso_cookie_domains:
        response.delete_cookie(key=settings.sso_cookie_name, domain=domain, path="/")
    return {"detail": "logged out"}


@router.get("/verify", include_in_schema=False)
async def verify_sso(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    """Checked by nginx's auth_request before routing to any household
    service - not part of the SPA's own API surface (see docs/architecture.md
    Household Services SSO note)."""
    user = await _sso_user(request, db)
    return Response(status_code=200 if user else 401)


@router.get("/wallabag-sso", include_in_schema=False)
async def wallabag_sso(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    """Auto-login bridge for Wallabag's one shared account - Wallabag has no
    reverse-proxy/OIDC pre-auth of its own (see docs/decisions.md), so this
    logs in server-side and hands the browser the resulting session cookie.
    Linked from the dashboard's Household Services tile instead of Wallabag
    directly."""
    user = await _sso_user(request, db)
    if user is None:
        return RedirectResponse(f"http://{_platform_root(request)}/login")

    session_id = await WallabagBridgeService().login()
    if session_id is None:
        return RedirectResponse("https://wallabag.cluster.download/login")

    response = RedirectResponse("https://wallabag.cluster.download/")
    for domain in settings.sso_cookie_domains:
        response.set_cookie(
            key="PHPSESSID", value=session_id, domain=domain, path="/",
            httponly=True, samesite="lax",
        )
    return response


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
