import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings
from app.database import AsyncSessionLocal
from app.repositories.alert_history_repository import AlertHistoryRepository

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 30


async def poll_alert_history_forever() -> None:
    while True:
        try:
            await _sync_alerts()
        except Exception as e:
            logger.error("Alert history sync error: %s", e)
        await asyncio.sleep(_POLL_INTERVAL)


async def _sync_alerts() -> None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.prometheus_url}/api/v1/alerts")
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("Alert history: Prometheus unreachable — %s", e)
        return

    # Build map of currently firing alerts keyed by (alert_name, node_name)
    current: dict[tuple[str, str | None], dict] = {}
    for a in data.get("data", {}).get("alerts", []):
        if a.get("state") != "firing":
            continue
        labels = a.get("labels", {})
        name = labels.get("alertname", "Unknown")
        node_name = labels.get("node_name") or None
        instance = labels.get("instance") or None
        severity = labels.get("severity", "info")
        summary = a.get("annotations", {}).get("summary") or None
        try:
            fired_at = datetime.fromisoformat(a["activeAt"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            fired_at = datetime.now(timezone.utc)
        key = (name, node_name)
        current[key] = {
            "alert_name": name,
            "severity": severity,
            "node_name": node_name,
            "instance": instance,
            "summary": summary,
            "labels": json.dumps(labels),
            "fired_at": fired_at,
        }

    async with AsyncSessionLocal() as db:
        repo = AlertHistoryRepository(db)
        open_entries = await repo.get_open()
        open_map: dict[tuple[str, str | None], int] = {
            (e.alert_name, e.node_name): e.id for e in open_entries
        }

        # New firings not yet in DB
        for key, info in current.items():
            if key not in open_map:
                await repo.create_firing(**info)
                logger.info("Alert history: recorded firing %s node=%s", key[0], key[1])
                try:
                    from app.services.notification_service import dispatch_alert_notification
                    await dispatch_alert_notification(
                        alert_name=info["alert_name"],
                        severity=info["severity"],
                        summary=info.get("summary"),
                        node_name=info.get("node_name"),
                    )
                except Exception as e:
                    logger.warning("Failed to dispatch notification: %s", e)

        # Resolved alerts — stamp resolved_at
        now = datetime.now(timezone.utc)
        for key, entry_id in open_map.items():
            if key not in current:
                await repo.resolve_firing(entry_id, now)
                logger.info("Alert history: resolved %s node=%s", key[0], key[1])
