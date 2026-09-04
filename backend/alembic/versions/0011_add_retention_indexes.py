"""add indexes for log retention cleanup

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-04
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(ix["name"] == index_name for ix in inspector.get_indexes(table_name))


def upgrade() -> None:
    # Idempotent: a prior interrupted run of this migration (or manual
    # intervention) may have already created one of these indexes without
    # alembic_version having advanced to 0011.
    if not _index_exists("audit_logs", "ix_audit_logs_created_at"):
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    if not _index_exists("alert_history", "ix_alert_history_resolved_at"):
        op.create_index("ix_alert_history_resolved_at", "alert_history", ["resolved_at"])


def downgrade() -> None:
    if _index_exists("alert_history", "ix_alert_history_resolved_at"):
        op.drop_index("ix_alert_history_resolved_at", "alert_history")
    if _index_exists("audit_logs", "ix_audit_logs_created_at"):
        op.drop_index("ix_audit_logs_created_at", "audit_logs")
