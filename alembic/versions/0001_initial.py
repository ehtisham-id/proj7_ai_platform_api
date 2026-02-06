"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums explicitly, then reuse them without re-creating on table DDL
    # Create enums only if they don't exist (idempotent across retries)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role') THEN
                CREATE TYPE role AS ENUM ('user', 'admin');
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'jobstatus') THEN
                CREATE TYPE jobstatus AS ENUM ('pending', 'completed', 'failed');
            END IF;
        END$$;
        """
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("user", "admin", name="role", create_type=False),
            nullable=True,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("bucket", sa.String(), nullable=True),
        sa.Column("object_name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_files_object_name", "files", ["object_name"], unique=True)

    op.create_table(
        "file_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("files.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("object_name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "completed", "failed", name="jobstatus", create_type=False),
            nullable=True,
        ),
        sa.Column("result_url", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("jobs")
    op.drop_table("file_versions")
    op.drop_index("ix_files_object_name", table_name="files")
    op.drop_table("files")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    postgresql.ENUM(name="jobstatus").drop(bind, checkfirst=True)
    postgresql.ENUM(name="role").drop(bind, checkfirst=True)
