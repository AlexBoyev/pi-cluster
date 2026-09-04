"""Retention cleanup: repository-level deletes and the daily cleanup job."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from app.repositories.audit_repository import AuditRepository
from app.repositories.alert_history_repository import AlertHistoryRepository


@pytest.mark.asyncio
async def test_delete_older_than_removes_only_old_audit_rows(test_session_factory):
    async with test_session_factory() as db:
        repo = AuditRepository(db)
        old = await repo.create(
            action="workload.create", resource_type="workload",
            resource_name="retention-old", actor="tester", status="success",
        )
        recent = await repo.create(
            action="workload.create", resource_type="workload",
            resource_name="retention-recent", actor="tester", status="success",
        )
        # Backdate the "old" row directly — created_at has a server default.
        old.created_at = datetime.now(timezone.utc) - timedelta(days=200)
        await db.commit()

        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        deleted = await repo.delete_older_than(cutoff)
        assert deleted >= 1

        remaining = await repo.get_recent(limit=500)
        names = {e.resource_name for e in remaining}
        assert "retention-old" not in names
        assert "retention-recent" in names


@pytest.mark.asyncio
async def test_delete_resolved_older_than_keeps_active_alerts(test_session_factory):
    async with test_session_factory() as db:
        repo = AlertHistoryRepository(db)
        now = datetime.now(timezone.utc)

        old_resolved = await repo.create_firing(
            alert_name="retention-old-resolved", severity="warning",
            fired_at=now - timedelta(days=200), node_name="pi-node2",
        )
        await repo.resolve_firing(old_resolved.id, now - timedelta(days=199))

        recent_resolved = await repo.create_firing(
            alert_name="retention-recent-resolved", severity="warning",
            fired_at=now - timedelta(days=1), node_name="pi-node2",
        )
        await repo.resolve_firing(recent_resolved.id, now)

        still_active = await repo.create_firing(
            alert_name="retention-still-active", severity="critical",
            fired_at=now - timedelta(days=200), node_name="pi-node3",
        )

        cutoff = now - timedelta(days=90)
        deleted = await repo.delete_resolved_older_than(cutoff)
        assert deleted >= 1

        remaining = await repo.get_recent(limit=500)
        names = {e.alert_name for e in remaining}
        assert "retention-old-resolved" not in names
        assert "retention-recent-resolved" in names
        # Active alerts survive regardless of age — never auto-deleted.
        assert "retention-still-active" in names


@pytest.mark.asyncio
async def test_cleanup_once_uses_configured_retention_days():
    from app.services.retention_service import _cleanup_once

    with patch("app.services.retention_service.AuditRepository") as MockAudit, \
         patch("app.services.retention_service.AlertHistoryRepository") as MockAlerts:
        MockAudit.return_value.delete_older_than = AsyncMock(return_value=0)
        MockAlerts.return_value.delete_resolved_older_than = AsyncMock(return_value=0)
        await _cleanup_once()

    MockAudit.return_value.delete_older_than.assert_called_once()
    MockAlerts.return_value.delete_resolved_older_than.assert_called_once()
