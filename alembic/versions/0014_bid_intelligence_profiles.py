"""Add bidder profiles and compliance mappings."""

from alembic import op
import sqlalchemy as sa

revision = "0014_bid_intelligence_profiles"
down_revision = "0013_formula_configs"


def upgrade() -> None:
    op.create_table(
        "bidder_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("legal_entity", sa.String(500), nullable=False),
        sa.Column("parent_entity", sa.String(500)),
        sa.Column("consortium_members", sa.JSON(), nullable=False),
        sa.Column("oem_associations", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "bid_compliance_mappings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("compliance_state", sa.String(64), nullable=False),
        sa.Column("rationale", sa.Text()),
        sa.Column("evidence_document_id", sa.Uuid()),
        sa.Column("determined_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "project_id", "requirement_id", name="uq_bid_compliance_project_requirement"
        ),
    )
