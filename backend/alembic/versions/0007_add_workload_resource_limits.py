"""add workload resource limits

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-29
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workloads", sa.Column("cpu_limit", sa.String(16), nullable=False, server_default="500m"))
    op.add_column("workloads", sa.Column("memory_limit", sa.String(16), nullable=False, server_default="256Mi"))


def downgrade() -> None:
    op.drop_column("workloads", "memory_limit")
    op.drop_column("workloads", "cpu_limit")
