"""Add structured requirements and evidence provenance."""

from alembic import op
import sqlalchemy as sa

revision = "0008_structured_requirements_evidence"
down_revision = "0007_document_metadata_relationships"


def upgrade() -> None:
    with op.batch_alter_table("evidence_spans") as batch_op:
        batch_op.add_column(sa.Column("coordinates", sa.JSON()))
        batch_op.add_column(
            sa.Column(
                "extraction_method",
                sa.String(32),
                nullable=False,
                server_default="human_transcription",
            )
        )
        batch_op.add_column(sa.Column("extraction_version", sa.String(100)))
        batch_op.add_column(sa.Column("confidence", sa.Float()))
        batch_op.add_column(sa.Column("created_by", sa.Uuid()))
        batch_op.add_column(sa.Column("verified_by", sa.Uuid()))
        batch_op.add_column(sa.Column("verified_at", sa.DateTime(timezone=True)))
        batch_op.add_column(sa.Column("verification_note", sa.Text()))
    for name, column in [
        ("requirement_type", sa.String(64)),
        ("title", sa.String(500)),
        ("metric", sa.String(200)),
        ("comparator", sa.String(32)),
        ("threshold", sa.String(200)),
        ("minimum_value", sa.Float()),
        ("maximum_value", sa.Float()),
        ("unit", sa.String(64)),
        ("measurement_boundary", sa.String(500)),
        ("measurement_point", sa.String(500)),
        ("measurement_period", sa.String(500)),
        ("test_method", sa.Text()),
        ("mandatory", sa.Boolean()),
        ("evidence_required", sa.Text()),
        ("contractual_consequence", sa.Text()),
        ("responsible_party", sa.String(200)),
        ("applicability_condition", sa.Text()),
        ("applicable_start_year", sa.Integer()),
        ("applicable_end_year", sa.Integer()),
        ("materiality", sa.String(32)),
        ("owner_discipline", sa.String(64)),
        ("created_by", sa.Uuid()),
        ("approved_by", sa.Uuid()),
        ("created_at", sa.DateTime(timezone=True)),
        ("approved_at", sa.DateTime(timezone=True)),
    ]:
        op.add_column("requirements", sa.Column(name, column))
    op.add_column(
        "requirements",
        sa.Column(
            "evaluation_treatment", sa.String(32), nullable=False, server_default="not_specified"
        ),
    )


def downgrade() -> None:
    op.drop_column("requirements", "evaluation_treatment")
    for name in [
        "approved_at",
        "created_at",
        "approved_by",
        "created_by",
        "owner_discipline",
        "materiality",
        "applicable_end_year",
        "applicable_start_year",
        "applicability_condition",
        "responsible_party",
        "contractual_consequence",
        "evidence_required",
        "mandatory",
        "test_method",
        "measurement_period",
        "measurement_point",
        "measurement_boundary",
        "unit",
        "maximum_value",
        "minimum_value",
        "threshold",
        "comparator",
        "metric",
        "title",
        "requirement_type",
    ]:
        op.drop_column("requirements", name)
    with op.batch_alter_table("evidence_spans") as batch_op:
        for name in [
            "verification_note",
            "verified_at",
            "verified_by",
            "created_by",
            "confidence",
            "extraction_version",
            "extraction_method",
            "coordinates",
        ]:
            batch_op.drop_column(name)
