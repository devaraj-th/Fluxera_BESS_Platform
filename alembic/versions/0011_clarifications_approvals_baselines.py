"""Add clarification, approval, and immutable baseline records."""

from alembic import op
import sqlalchemy as sa

revision = "0011_clarifications_approvals_baselines"
down_revision = "0010_persisted_findings"


def upgrade() -> None:
    op.create_table(
        "clarifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("finding_id", sa.Uuid(), sa.ForeignKey("findings.id")),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text()),
        sa.Column("proposed_wording", sa.Text()),
        sa.Column("owner", sa.String(200)),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("buyer_response", sa.Text()),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clarifications_project_status", "clarifications", ["project_id", "status"])
    op.create_table(
        "approval_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("object_type", sa.String(100), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("object_version", sa.Integer()),
        sa.Column("decision", sa.String(64), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("previous_state", sa.String(64)),
        sa.Column("new_state", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_approvals_project_created", "approval_records", ["project_id", "created_at"]
    )
    op.create_table(
        "baselines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("frozen_by", sa.Uuid(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "version", name="uq_baseline_project_version"),
    )


def downgrade() -> None:
    op.drop_table("baselines")
    op.drop_index("ix_approvals_project_created", table_name="approval_records")
    op.drop_table("approval_records")
    op.drop_index("ix_clarifications_project_status", table_name="clarifications")
    op.drop_table("clarifications")
