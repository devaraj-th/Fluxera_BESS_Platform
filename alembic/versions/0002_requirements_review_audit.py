"""Requirement review and audit records."""
from alembic import op
import sqlalchemy as sa

revision = "0002_requirements_review_audit"
down_revision = "0001_initial"


def uuid_type():
    return sa.Uuid()


def upgrade() -> None:
    op.create_table("requirements", sa.Column("id", uuid_type(), primary_key=True), sa.Column("tenant_id", uuid_type(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("project_id", uuid_type(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("stable_key", sa.String(32), nullable=False), sa.Column("taxonomy", sa.String(3), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("state", sa.String(32), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.UniqueConstraint("project_id", "stable_key", name="uq_requirement_project_key"))
    op.create_table("requirement_evidence", sa.Column("requirement_id", uuid_type(), sa.ForeignKey("requirements.id"), primary_key=True), sa.Column("evidence_span_id", uuid_type(), sa.ForeignKey("evidence_spans.id"), primary_key=True), sa.Column("verified", sa.Boolean(), nullable=False))
    op.create_table("review_decisions", sa.Column("id", uuid_type(), primary_key=True), sa.Column("requirement_id", uuid_type(), sa.ForeignKey("requirements.id"), nullable=False), sa.Column("actor_id", uuid_type(), nullable=False), sa.Column("decision", sa.String(32), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("audit_events", sa.Column("id", uuid_type(), primary_key=True), sa.Column("tenant_id", uuid_type(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("project_id", uuid_type(), sa.ForeignKey("projects.id"), nullable=False), sa.Column("actor_id", uuid_type(), nullable=False), sa.Column("action", sa.String(100), nullable=False), sa.Column("object_type", sa.String(100), nullable=False), sa.Column("object_id", uuid_type(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("review_decisions")
    op.drop_table("requirement_evidence")
    op.drop_table("requirements")
