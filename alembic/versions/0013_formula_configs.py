"""Persist Formula Lab configuration versions and linked calculation history."""

from alembic import op
import sqlalchemy as sa

revision = "0013_formula_configs"
down_revision = "0012_formula_calculations"


def upgrade() -> None:
    op.create_table(
        "formula_configs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_clause_text", sa.Text()),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by", sa.Uuid()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "version", name="uq_formula_config_project_version"),
    )
    op.create_index(
        "ix_formula_configs_project_version", "formula_configs", ["project_id", "version"]
    )
    with op.batch_alter_table("formula_calculations") as batch_op:
        batch_op.add_column(sa.Column("formula_config_id", sa.Uuid()))
        batch_op.create_foreign_key(
            "fk_formula_calculations_formula_config_id",
            "formula_configs",
            ["formula_config_id"],
            ["id"],
        )
    op.create_index(
        "ix_formula_calculations_config_created",
        "formula_calculations",
        ["formula_config_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_formula_calculations_config_created", table_name="formula_calculations")
    with op.batch_alter_table("formula_calculations") as batch_op:
        batch_op.drop_constraint("fk_formula_calculations_formula_config_id", type_="foreignkey")
        batch_op.drop_column("formula_config_id")
    op.drop_index("ix_formula_configs_project_version", table_name="formula_configs")
    op.drop_table("formula_configs")
