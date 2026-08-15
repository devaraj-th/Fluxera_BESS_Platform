"""Add persisted deterministic findings."""

from alembic import op
import sqlalchemy as sa

revision = "0010_persisted_findings"
down_revision = "0009_project_mode_archetype"


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("finding_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("affected_objects", sa.JSON(), nullable=False),
        sa.Column("source_evidence", sa.JSON(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False, server_default="open"),
        sa.Column("assigned_owner", sa.String(200)),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_by", sa.Uuid()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_findings_project_state", "findings", ["project_id", "state"])


def downgrade() -> None:
    op.drop_index("ix_findings_project_state", table_name="findings")
    op.drop_table("findings")
