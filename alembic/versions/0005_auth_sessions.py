"""Add password and revocable session authentication."""

from alembic import op
import sqlalchemy as sa

revision = "0005_auth_sessions"
down_revision = "0004_users_memberships"


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(512)))
    op.add_column("users", sa.Column("disabled_at", sa.DateTime(timezone=True)))
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_column("users", "disabled_at")
    op.drop_column("users", "password_hash")
