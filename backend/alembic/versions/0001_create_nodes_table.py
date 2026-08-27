"""create nodes table

Revision ID: 0001
Revises:
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE nodestatus AS ENUM ('ONLINE', 'OFFLINE', 'DEGRADED', 'UNKNOWN');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(64)  NOT NULL UNIQUE,
            ip_address  VARCHAR(45)  NOT NULL,
            status      nodestatus   NOT NULL DEFAULT 'UNKNOWN',
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS nodes")
    op.execute("DROP TYPE IF EXISTS nodestatus")
