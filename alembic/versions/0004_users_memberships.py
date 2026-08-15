"""Add tenant membership records for server-side authorization."""

from alembic import op
import sqlalchemy as sa

revision = "0004_users_memberships"
down_revision = "0003_evidence_timestamps_indexes"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
    )
    op.create_table(
        "memberships",
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("memberships")
    op.drop_table("users")
