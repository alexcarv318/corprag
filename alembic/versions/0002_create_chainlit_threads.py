"""create chainlit thread tables

Revision ID: 0002_create_chainlit_threads
Revises: 0001_create_users
Create Date: 2026-06-14
"""

from alembic import op

revision = "0002_create_chainlit_threads"
down_revision = "0001_create_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS threads (
            "id" UUID PRIMARY KEY,
            "createdAt" TEXT,
            "name" TEXT,
            "userId" UUID,
            "userIdentifier" TEXT,
            "tags" TEXT[],
            "metadata" JSONB,
            FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS steps (
            "id" UUID PRIMARY KEY,
            "name" TEXT NOT NULL,
            "type" TEXT NOT NULL,
            "threadId" UUID NOT NULL,
            "parentId" UUID,
            "streaming" BOOLEAN NOT NULL,
            "waitForAnswer" BOOLEAN,
            "isError" BOOLEAN,
            "metadata" JSONB,
            "tags" TEXT[],
            "input" TEXT,
            "output" TEXT,
            "createdAt" TEXT,
            "command" TEXT,
            "start" TEXT,
            "end" TEXT,
            "generation" JSONB,
            "showInput" TEXT,
            "language" TEXT,
            "indent" INT,
            "defaultOpen" BOOLEAN,
            "autoCollapse" BOOLEAN,
            "modes" JSONB,
            FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS elements (
            "id" UUID PRIMARY KEY,
            "threadId" UUID,
            "type" TEXT,
            "url" TEXT,
            "chainlitKey" TEXT,
            "name" TEXT NOT NULL,
            "display" TEXT,
            "objectKey" TEXT,
            "size" TEXT,
            "page" INT,
            "language" TEXT,
            "forId" UUID,
            "mime" TEXT,
            "props" JSONB,
            FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS feedbacks (
            "id" UUID PRIMARY KEY,
            "forId" UUID NOT NULL,
            "threadId" UUID NOT NULL,
            "value" INT NOT NULL,
            "comment" TEXT,
            FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feedbacks")
    op.execute("DROP TABLE IF EXISTS elements")
    op.execute("DROP TABLE IF EXISTS steps")
    op.execute("DROP TABLE IF EXISTS threads")
