"""Add procurement project mode and archetype metadata."""

from alembic import op
import sqlalchemy as sa

revision = "0009_project_mode_archetype"
down_revision = "0008_structured_requirements_evidence"


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(
            sa.Column("module_mode", sa.String(32), nullable=False, server_default="pre_bid")
        )
        batch_op.add_column(
            sa.Column(
                "procurement_archetype", sa.String(64), nullable=False, server_default="custom"
            )
        )
        batch_op.add_column(sa.Column("tender_number", sa.String(200)))
        batch_op.add_column(sa.Column("procuring_organization", sa.String(200)))
        batch_op.add_column(sa.Column("jurisdiction", sa.String(200)))
        batch_op.add_column(sa.Column("currency", sa.String(3)))
        batch_op.add_column(
            sa.Column("status", sa.String(32), nullable=False, server_default="draft")
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("status")
        batch_op.drop_column("currency")
        batch_op.drop_column("jurisdiction")
        batch_op.drop_column("procuring_organization")
        batch_op.drop_column("tender_number")
        batch_op.drop_column("procurement_archetype")
        batch_op.drop_column("module_mode")
