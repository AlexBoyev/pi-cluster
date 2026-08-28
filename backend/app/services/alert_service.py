import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.schemas.alert import AlertResponse

logger = logging.getLogger(__name__)


class AlertService:
    async def get_alerts(self) -> list[AlertResponse]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.prometheus_url}/api/v1/alerts")
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Failed to fetch alerts from Prometheus: %s", e)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Prometheus unreachable",
            )

        now = datetime.now(timezone.utc)
        alerts: list[AlertResponse] = []
        for a in data.get("data", {}).get("alerts", []):
            labels = a.get("labels", {})
            annotations = a.get("annotations", {})
            try:
                fired_at = datetime.fromisoformat(a["activeAt"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                fired_at = now
            alerts.append(AlertResponse(
                name=labels.get("alertname", "Unknown"),
                severity=labels.get("severity", "info"),
                state=a.get("state", "firing"),
                node_name=labels.get("node_name"),
                summary=annotations.get("summary", ""),
                description=annotations.get("description", ""),
                fired_at=fired_at,
                duration_seconds=max(0, int((now - fired_at).total_seconds())),
            ))

        return sorted(alerts, key=lambda x: (x.severity != "critical", x.fired_at))
