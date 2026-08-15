"""Persist Formula Lab calculations."""

from alembic import op
import sqlalchemy as sa

revision = "0012_formula_calculations"
down_revision = "0011_clarifications_approvals_baselines"


def upgrade() -> None:
    op.create_table(
        "formula_calculations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("output_value", sa.String(100), nullable=False),
        sa.Column("reproducibility_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("formula_calculations")
