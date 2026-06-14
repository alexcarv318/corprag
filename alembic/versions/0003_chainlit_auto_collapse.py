"""add chainlit step auto collapse column

Revision ID: 0003_chainlit_auto_collapse
Revises: 0002_create_chainlit_threads
Create Date: 2026-06-14
"""

from alembic import op

revision = "0003_chainlit_auto_collapse"
down_revision = "0002_create_chainlit_threads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE steps
        ADD COLUMN IF NOT EXISTS "autoCollapse" BOOLEAN
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE steps
        DROP COLUMN IF EXISTS "autoCollapse"
        """
    )
