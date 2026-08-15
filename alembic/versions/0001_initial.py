"""Initial tenant-scoped evidence schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None


def uuid_type():
    return sa.Uuid()


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
    )
    op.create_table(
        "projects",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("tenant_id", uuid_type(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_project_tenant_name"),
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])
    op.create_table(
        "documents",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("tenant_id", uuid_type(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", uuid_type(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "sha256", name="uq_document_project_hash"),
    )
    op.create_table(
        "pages",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("document_id", uuid_type(), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("document_id", "page_number", name="uq_page_document_number"),
    )
    op.create_index("ix_pages_document_order", "pages", ["document_id", "page_number"])
    op.create_table(
        "evidence_spans",
        sa.Column("id", uuid_type(), primary_key=True),
        sa.Column("tenant_id", uuid_type(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("project_id", uuid_type(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("page_id", uuid_type(), sa.ForeignKey("pages.id"), nullable=False),
        sa.Column("exact_text", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer()),
        sa.Column("end_offset", sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table("evidence_spans")
    op.drop_index("ix_pages_document_order", table_name="pages")
    op.drop_table("pages")
    op.drop_table("documents")
    op.drop_index("ix_projects_tenant_id", table_name="projects")
    op.drop_table("projects")
    op.drop_table("tenants")
