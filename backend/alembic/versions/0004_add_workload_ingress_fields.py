"""add workload ingress fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workloads", sa.Column("container_port", sa.Integer, nullable=True))
    op.add_column("workloads", sa.Column("ingress_host", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("workloads", "ingress_host")
    op.drop_column("workloads", "container_port")
