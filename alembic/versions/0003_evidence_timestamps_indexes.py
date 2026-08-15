"""Add evidence timestamps and scoped query indexes."""

from alembic import op
import sqlalchemy as sa

revision = "0003_evidence_timestamps_indexes"
down_revision = "0002_requirements_review_audit"


def upgrade() -> None:
    now = sa.text("CURRENT_TIMESTAMP")
    op.add_column(
        "pages",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=now),
    )
    op.add_column(
        "evidence_spans",
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True, server_default=now),
    )
    with op.batch_alter_table("pages") as batch_op:
        batch_op.alter_column("created_at", nullable=False, server_default=None)
    with op.batch_alter_table("evidence_spans") as batch_op:
        batch_op.alter_column("created_at", nullable=False, server_default=None)
    op.create_index("ix_evidence_project_tenant", "evidence_spans", ["project_id", "tenant_id"])
    op.create_index("ix_audit_project_created", "audit_events", ["project_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_project_created", table_name="audit_events")
    op.drop_index("ix_evidence_project_tenant", table_name="evidence_spans")
    op.drop_column("evidence_spans", "created_at")
    op.drop_column("pages", "created_at")
