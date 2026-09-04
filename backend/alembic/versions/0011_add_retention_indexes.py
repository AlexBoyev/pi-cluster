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


def upgrade() -> None:
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_alert_history_resolved_at", "alert_history", ["resolved_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_history_resolved_at", "alert_history")
    op.drop_index("ix_audit_logs_created_at", "audit_logs")
