"""add workload health probes

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workloads", sa.Column("liveness_path", sa.String(255), nullable=True))
    op.add_column("workloads", sa.Column("readiness_path", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("workloads", "readiness_path")
    op.drop_column("workloads", "liveness_path")
