"""create users table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('admin', 'viewer');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id               SERIAL PRIMARY KEY,
            username         VARCHAR(64)  NOT NULL UNIQUE,
            hashed_password  VARCHAR(128) NOT NULL,
            role             userrole     NOT NULL DEFAULT 'viewer',
            is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_username")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS userrole")
