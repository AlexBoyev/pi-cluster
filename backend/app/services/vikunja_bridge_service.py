import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Same worker list nginx's traefik_workers upstream uses (nginx/nginx.conf) -
# called directly here, bypassing nginx's own SSO gate, since this request
# is what establishes that gate's pass-through in the first place.
_TRAEFIK_WORKERS = ["10.100.102.16", "10.100.102.17", "10.100.102.12"]
_VIKUNJA_HOST = "vikunja.cluster.download"


class VikunjaBridgeService:
    """Auto-login bridge for Vikunja. Unlike Wallabag's single shared
    account, Vikunja has two real distinct accounts (docs/decisions.md), so
    this looks up the calling pi-cluster user's own Vikunja login from a
    per-user lookup table (settings.vikunja_bridge_credentials) instead of
    one fixed value for everyone. A user with no entry in the table simply
    gets no bridge - falls through to Vikunja's own login screen, same as
    before any bridge existed."""

    async def login(self, pi_cluster_username: str) -> tuple[str, str] | None:
        """Returns (refresh_token, access_token) - both are needed. The
        refresh_token cookie alone was confirmed live to NOT be enough:
        Vikunja's frontend only attempts a cookie-based silent refresh from
        inside checkAuth() when it finds an *already-stored, expired* JWT
        under localStorage['token'] - on a genuinely fresh load (nothing in
        localStorage, e.g. incognito) it never calls the refresh endpoint at
        all and just renders /login. Confirmed via Vikunja's own access
        logs: real browser hits only ever showed GET /login, never POST
        /api/v1/user/token/refresh, while curl calling refresh directly
        with the same cookie succeeded every time. So the access_token from
        the login response body has to be injected into localStorage
        directly - see vikunja_sso_finish."""
        vikunja_login = settings.vikunja_bridge_credentials.get(pi_cluster_username)
        if vikunja_login is None:
            logger.info("vikunja-sso bridge: no entry mapped for %s", pi_cluster_username)
            return None
        for worker in _TRAEFIK_WORKERS:
            tokens = await self._try_worker(worker, pi_cluster_username, vikunja_login)
            if tokens:
                return tokens
        logger.warning(
            "vikunja-sso bridge: all %d workers failed for %s",
            len(_TRAEFIK_WORKERS), pi_cluster_username,
        )
        return None

    async def _try_worker(
        self, worker: str, username: str, vikunja_login: str
    ) -> tuple[str, str] | None:
        base = f"http://{worker}"
        headers = {"Host": _VIKUNJA_HOST}
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as client:
                resp = await client.post(
                    f"{base}/api/v1/login",
                    headers=headers,
                    json={"username": username, "password": vikunja_login},
                )
                if resp.status_code != 200:
                    logger.warning(
                        "vikunja-sso bridge: %s login for %s -> %d",
                        worker, username, resp.status_code,
                    )
                    return None
                access_token = resp.json().get("token")
                if not access_token:
                    logger.warning(
                        "vikunja-sso bridge: %s login for %s had no token in body",
                        worker, username,
                    )
                    return None
                # Vikunja sends this cookie twice (Path=/api/v1/... and
                # Path=/api/v2/...) with the same value - resp.cookies.get()
                # raises CookieConflict on the duplicate name (confirmed
                # live, not a hypothetical), so pull it from the jar
                # directly instead of the ambiguous by-name lookup.
                for cookie in resp.cookies.jar:
                    if cookie.name == "vikunja_refresh_token":
                        return cookie.value, access_token
                return None
        except httpx.HTTPError as exc:
            logger.warning("vikunja-sso bridge: %s request failed: %s", worker, exc)
            return None
