"""Add versioned project Design Basis."""

from alembic import op
import sqlalchemy as sa

revision = "0006_design_basis_versions"
down_revision = "0005_auth_sessions"


def upgrade() -> None:
    op.create_table(
        "design_basis_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.Uuid()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("project_id", "version", name="uq_design_basis_project_version"),
    )
    op.create_index("ix_design_basis_project", "design_basis_versions", ["project_id", "version"])


def downgrade() -> None:
    op.drop_index("ix_design_basis_project", table_name="design_basis_versions")
    op.drop_table("design_basis_versions")
