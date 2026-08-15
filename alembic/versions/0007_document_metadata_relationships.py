"""Add document version metadata and cross-document relationships."""

from alembic import op
import sqlalchemy as sa

revision = "0007_document_metadata_relationships"
down_revision = "0006_design_basis_versions"


def upgrade() -> None:
    op.create_table(
        "document_families",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_document_families_project", "document_families", ["project_id", "created_at"]
    )
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(sa.Column("family_id", sa.Uuid()))
        batch_op.create_foreign_key(
            "fk_documents_family_id_document_families",
            "document_families",
            ["family_id"],
            ["id"],
        )
        batch_op.add_column(
            sa.Column("document_type", sa.String(64), nullable=False, server_default="other")
        )
        batch_op.add_column(sa.Column("volume", sa.String(100)))
        batch_op.add_column(sa.Column("title", sa.String(500)))
        batch_op.add_column(sa.Column("revision", sa.String(100)))
        batch_op.add_column(sa.Column("issue_date", sa.Date()))
        batch_op.add_column(sa.Column("effective_date", sa.Date()))
        batch_op.add_column(sa.Column("tender_number", sa.String(200)))
        batch_op.add_column(sa.Column("addendum_number", sa.String(100)))
        batch_op.add_column(sa.Column("corrigendum_number", sa.String(100)))
        batch_op.add_column(sa.Column("parser_version", sa.String(100)))
        batch_op.add_column(sa.Column("ocr_version", sa.String(100)))
        batch_op.add_column(
            sa.Column("page_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("review_status", sa.String(32), nullable=False, server_default="pending")
        )
        batch_op.add_column(
            sa.Column(
                "controlling_status",
                sa.String(32),
                nullable=False,
                server_default="not_controlling",
            )
        )
        batch_op.add_column(sa.Column("uploaded_by", sa.Uuid()))
    op.create_index("ix_documents_project_family", "documents", ["project_id", "family_id"])
    op.create_table(
        "document_relationships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("target_document_id", sa.Uuid(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("relationship_type", sa.String(32), nullable=False),
        sa.Column("affected_clauses", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewer_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_document_id",
            "target_document_id",
            "relationship_type",
            name="uq_document_relationship",
        ),
    )
    op.create_index(
        "ix_document_relationships_project", "document_relationships", ["project_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_document_relationships_project", table_name="document_relationships")
    op.drop_table("document_relationships")
    op.drop_index("ix_documents_project_family", table_name="documents")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_constraint("fk_documents_family_id_document_families", type_="foreignkey")
        batch_op.drop_column("uploaded_by")
        batch_op.drop_column("controlling_status")
        batch_op.drop_column("review_status")
        batch_op.drop_column("page_count")
        batch_op.drop_column("ocr_version")
        batch_op.drop_column("parser_version")
        batch_op.drop_column("corrigendum_number")
        batch_op.drop_column("addendum_number")
        batch_op.drop_column("tender_number")
        batch_op.drop_column("effective_date")
        batch_op.drop_column("issue_date")
        batch_op.drop_column("revision")
        batch_op.drop_column("title")
        batch_op.drop_column("volume")
        batch_op.drop_column("document_type")
        batch_op.drop_column("family_id")
    op.drop_index("ix_document_families_project", table_name="document_families")
    op.drop_table("document_families")
