"""create alert_history table

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alert_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("alert_name", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("node_name", sa.String(128), nullable=True),
        sa.Column("instance", sa.String(255), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("labels", sa.Text, nullable=True),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_alert_history_fired_at", "alert_history", ["fired_at"])
    op.create_index("ix_alert_history_alert_name", "alert_history", ["alert_name"])


def downgrade() -> None:
    op.drop_index("ix_alert_history_alert_name", "alert_history")
    op.drop_index("ix_alert_history_fired_at", "alert_history")
    op.drop_table("alert_history")
