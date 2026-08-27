"""create nodes table

Revision ID: 0001
Revises:
Create Date: 2026-08-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False prevents op.create_table from creating the enum again
# after node_status.create() already did it with checkfirst=True.
node_status = sa.Enum("ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN", name="nodestatus")
node_status_col = sa.Enum("ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN", name="nodestatus", create_type=False)


def upgrade() -> None:
    node_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("status", node_status_col, nullable=False, server_default="UNKNOWN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )


def downgrade() -> None:
    op.drop_table("nodes")
    node_status.drop(op.get_bind(), checkfirst=True)
