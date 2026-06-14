"""create users

Revision ID: 0001_create_users
Revises:
Create Date: 2026-06-14
"""

from alembic import op

revision = "0001_create_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE users (
            id UUID PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE users")
