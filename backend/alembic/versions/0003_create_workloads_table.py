"""create workloads table

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE workloadstatus AS ENUM ('pending', 'running', 'failed', 'deleted')")
    op.create_table(
        "workloads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), unique=True, nullable=False),
        sa.Column("namespace", sa.String(64), nullable=False),
        sa.Column("image", sa.String(255), nullable=False),
        sa.Column("replicas", sa.Integer, nullable=False),
        sa.Column("target_node", sa.String(64), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "failed", "deleted", name="workloadstatus", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("workloads")
    op.execute("DROP TYPE workloadstatus")
