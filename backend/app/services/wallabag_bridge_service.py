import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Same worker list nginx's traefik_workers upstream uses (nginx/nginx.conf) -
# called directly here, bypassing nginx's own SSO gate, since this request
# is what establishes that gate's pass-through in the first place.
_TRAEFIK_WORKERS = ["10.100.102.16", "10.100.102.17", "10.100.102.12"]
_WALLABAG_HOST = "wallabag.cluster.download"
_CSRF_RE = re.compile(r'name="_csrf_token" value="([^"]+)"')


class WallabagBridgeService:
    """Auto-login bridge for the single shared Wallabag account (see
    docs/decisions.md, SSO gate ADR). Logs in server-side with the stored
    account password and hands back the resulting session cookie value -
    never exposes that password to the browser."""

    async def login(self) -> str | None:
        for worker in _TRAEFIK_WORKERS:
            session_id = await self._try_worker(worker)
            if session_id:
                return session_id
        logger.warning("wallabag-sso bridge: all %d workers failed", len(_TRAEFIK_WORKERS))
        return None

    async def _try_worker(self, worker: str) -> str | None:
        base = f"http://{worker}"
        headers = {"Host": _WALLABAG_HOST}
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
                login_page = await client.get(f"{base}/login", headers=headers)
                if login_page.status_code != 200:
                    logger.warning(
                        "wallabag-sso bridge: %s GET /login -> %d", worker, login_page.status_code
                    )
                    return None
                match = _CSRF_RE.search(login_page.text)
                if not match:
                    logger.warning("wallabag-sso bridge: %s no CSRF token in /login page", worker)
                    return None
                resp = await client.post(
                    f"{base}/login_check",
                    headers=headers,
                    cookies=login_page.cookies,
                    data={
                        "_username": settings.wallabag_username,
                        "_password": settings.wallabag_password,
                        "_csrf_token": match.group(1),
                    },
                )
                session_id = resp.cookies.get("PHPSESSID")
                if not session_id:
                    logger.warning(
                        "wallabag-sso bridge: %s POST /login_check -> %d, no PHPSESSID"
                        " (bad credentials or CSRF mismatch)",
                        worker, resp.status_code,
                    )
                return session_id
        except httpx.HTTPError as exc:
            logger.warning("wallabag-sso bridge: %s request failed: %s", worker, exc)
            return None
