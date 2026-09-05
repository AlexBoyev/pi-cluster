"""add min_severity to notification_channels

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-05
"""
import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Only applies to dispatch_alert_notification (infra alerts) - never
    # filters dispatch_security_alert (new-login-IP etc, see
    # docs/decisions.md). "warning" (default) matches prior hardcoded
    # webhook behavior (unfiltered - warning is the lower of the two
    # severities in prometheus/alerts.yml, so this is a no-op default);
    # UI lets each channel pick "critical" to actually filter.
    op.add_column(
        "notification_channels",
        sa.Column(
            "min_severity", sa.String(16), nullable=False, server_default="warning"
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_channels", "min_severity")
