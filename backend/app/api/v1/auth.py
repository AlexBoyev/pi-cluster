from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    create_sso_token,
    create_vikunja_bridge_token,
    create_wallabag_bridge_token,
    decode_token,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.rate_limit import limiter
from app.repositories.known_login_ip_repository import KnownLoginIpRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessToken, LoginRequest, RefreshRequest, TokenPair, UserInfo
from app.services.notification_service import dispatch_security_alert
from app.services.vikunja_bridge_service import VikunjaBridgeService
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


def _client_ip(request: Request) -> str:
    # nginx sets this (real_client_ip - prefers Cloudflare's Cf-Connecting-Ip
    # for public traffic, falls back to $remote_addr for LAN-direct
    # requests - see nginx/nginx.conf). Vite's dev proxy forwards it
    # through unchanged. Fall back to the raw ASGI peer only if it's
    # missing entirely (e.g. a direct request bypassing nginx).
    header = request.headers.get("x-real-ip")
    if header:
        return header
    return request.client.host if request.client else "unknown"


def _platform_root(request: Request) -> str:
    # Vite's dev proxy rewrites Host before requests reach here
    # (changeOrigin: true) - nginx sets X-Forwarded-Host with the real one.
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
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

    ip = _client_ip(request)
    ip_repo = KnownLoginIpRepository(db)
    if not await ip_repo.is_known(user.id, ip):
        await dispatch_security_alert(
            "new_login_ip",
            f"{user.username} logged in from a new IP address: {ip}",
        )
    await ip_repo.record(user.id, ip)

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
    logs in server-side. Hands off to wallabag-sso-finish (below) rather
    than setting the PHPSESSID cookie itself: this endpoint is served from
    pi.cluster.download, which can only ever set that cookie broadly
    (Domain=.cluster.download) - and Wallabag's own login sets a host-only
    one. Two same-named cookies with different Domain scopes both get sent,
    and which one the server actually reads back is unpredictable - this
    was a real, reproduced bug, not a hypothetical. wallabag-sso-finish is
    reached via a redirect to wallabag.cluster.download itself, so it can
    set the cookie host-only, matching (and cleanly replacing) whatever
    Wallabag would set natively."""
    user = await _sso_user(request, db)
    if user is None:
        return RedirectResponse(f"http://{_platform_root(request)}/login")

    session_id = await WallabagBridgeService().login()
    if session_id is None:
        return RedirectResponse("https://wallabag.cluster.download/login")

    token = create_wallabag_bridge_token(session_id)
    return RedirectResponse(f"https://wallabag.cluster.download/__wallabag_sso_finish?t={token}")


@router.get("/wallabag-sso-finish", include_in_schema=False)
async def wallabag_sso_finish(t: str) -> Response:
    """Reached only via a redirect from wallabag-sso above, through nginx's
    `location = /__wallabag_sso_finish` (proxied here despite the public
    path being on wallabag.cluster.download - see nginx/nginx.conf) so this
    response is perceived by the browser as coming from Wallabag's own
    origin, letting the cookie below be set host-only."""
    try:
        payload = decode_token(t)
        if payload.get("type") != "wallabag_bridge":
            raise JWTError()
        session_id = payload["sid"]
    except JWTError:
        return RedirectResponse("https://wallabag.cluster.download/login")

    response = RedirectResponse("https://wallabag.cluster.download/")
    response.set_cookie(key="PHPSESSID", value=session_id, path="/", httponly=True, samesite="lax")
    return response


@router.get("/vikunja-sso", include_in_schema=False)
async def vikunja_sso(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    """Auto-login bridge for Vikunja. Unlike Wallabag, Vikunja has two real
    distinct accounts - VikunjaBridgeService looks up *this* pi-cluster
    user's own Vikunja password rather than one shared credential. Same
    two-hop handoff as the Wallabag bridge and for the same reason: this
    endpoint runs on pi.cluster.download, which can only set Vikunja's
    refresh-token cookie broadly - vikunja-sso-finish, reached via a
    redirect to vikunja.cluster.download itself, sets it host-only."""
    user = await _sso_user(request, db)
    if user is None:
        return RedirectResponse(f"http://{_platform_root(request)}/login")

    refresh_token = await VikunjaBridgeService().login(user.username)
    if refresh_token is None:
        return RedirectResponse("https://vikunja.cluster.download/login")

    token = create_vikunja_bridge_token(refresh_token)
    return RedirectResponse(f"https://vikunja.cluster.download/__vikunja_sso_finish?t={token}")


@router.get("/vikunja-sso-finish", include_in_schema=False)
async def vikunja_sso_finish(t: str) -> Response:
    """Reached only via a redirect from vikunja-sso above, through nginx's
    `location = /__vikunja_sso_finish` (see nginx/nginx.conf). Vikunja's own
    refresh-token cookie is Secure+SameSite=None (requires HTTPS) - this
    reissues it without Secure so it also works over the LAN's plain-http
    vikunja.pi-cluster.lan; Vikunja's server-side validation only checks the
    cookie's value, not the flags a browser stored it under."""
    try:
        payload = decode_token(t)
        if payload.get("type") != "vikunja_bridge":
            raise JWTError()
        refresh_token = payload["rt"]
    except JWTError:
        return RedirectResponse("https://vikunja.cluster.download/login")

    response = RedirectResponse("https://vikunja.cluster.download/")
    response.set_cookie(
        key="vikunja_refresh_token", value=refresh_token, path="/",
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
