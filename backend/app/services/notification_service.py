import logging

import httpx

from app.database import AsyncSessionLocal
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


async def dispatch_alert_notification(
    alert_name: str,
    severity: str,
    summary: str | None,
    node_name: str | None,
) -> None:
    async with AsyncSessionLocal() as db:
        channels = await NotificationRepository(db).list_enabled()

    if not channels:
        return

    payload = {
        "event": "alert_firing",
        "alert": alert_name,
        "severity": severity,
        "summary": summary or "",
        "node": node_name or "cluster",
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        for ch in channels:
            try:
                await client.post(ch.url, json=payload)
                logger.info("Notification sent to %s", ch.name)
            except Exception as e:
                logger.warning("Notification failed for %s: %s", ch.name, e)


async def test_channel(url: str) -> bool:
    payload = {"event": "test", "message": "Pi Cluster notification test"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code < 400
    except Exception:
        return False
