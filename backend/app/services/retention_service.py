import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import AsyncSessionLocal
from app.repositories.alert_history_repository import AlertHistoryRepository
from app.repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 24 * 60 * 60  # once a day


async def poll_retention_forever() -> None:
    while True:
        try:
            await _cleanup_once()
        except Exception as e:
            logger.error("Retention cleanup error: %s", e)
        await asyncio.sleep(_POLL_INTERVAL)


async def _cleanup_once() -> None:
    """Delete audit_logs and resolved alert_history rows older than
    LOG_RETENTION_DAYS. Scoped to these two DB-backed log tables only — other
    services (e.g. Loki, Prometheus) manage their own retention independently
    and are never touched here."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.log_retention_days)
    async with AsyncSessionLocal() as db:
        audit_deleted = await AuditRepository(db).delete_older_than(cutoff)
        alerts_deleted = await AlertHistoryRepository(db).delete_resolved_older_than(cutoff)
    if audit_deleted or alerts_deleted:
        logger.info(
            "Retention cleanup: removed %d audit_logs and %d resolved alert_history rows older than %d days",
            audit_deleted, alerts_deleted, settings.log_retention_days,
        )
