"""add email channel type to notification_channels, create known_login_ips

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-05
"""
import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing channels are all webhooks (url required, non-null); email
    # channels use email_address instead and leave url null - so url has to
    # become nullable rather than gaining a check constraint, to avoid
    # rewriting the column for existing rows.
    op.add_column(
        "notification_channels",
        sa.Column("channel_type", sa.String(16), nullable=False, server_default="webhook"),
    )
    op.add_column(
        "notification_channels",
        sa.Column("email_address", sa.String(255), nullable=True),
    )
    op.alter_column("notification_channels", "url", nullable=True)

    op.create_table(
        "known_login_ips",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.Column(
            "first_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_seen", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_known_login_ips_user_ip", "known_login_ips", ["user_id", "ip_address"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_known_login_ips_user_ip", table_name="known_login_ips")
    op.drop_table("known_login_ips")
    op.alter_column("notification_channels", "url", nullable=False)
    op.drop_column("notification_channels", "email_address")
    op.drop_column("notification_channels", "channel_type")
