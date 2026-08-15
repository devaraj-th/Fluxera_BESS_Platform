from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db import Base


class DocumentState(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PARSING = "parsing"
    PARSED = "parsed"
    REVIEW_READY = "review_ready"
    FAILED = "failed"
    REJECTED = "rejected"


class DocumentType(StrEnum):
    NIT = "nit"
    RFS = "rfs"
    RFP = "rfp"
    ITB = "itb"
    GCC = "gcc"
    SCC = "scc"
    TECHNICAL_SPECIFICATION = "technical_specification"
    BESPA = "bespa"
    BESSA = "bessa"
    PPA = "ppa"
    PRICE_SCHEDULE = "price_schedule"
    QUALIFICATION_FORMAT = "qualification_format"
    PRE_BID_QUERY = "pre_bid_query"
    PRE_BID_RESPONSE = "pre_bid_response"
    ADDENDUM = "addendum"
    CORRIGENDUM = "corrigendum"
    BID_TECHNICAL = "bid_technical"
    BID_COMMERCIAL = "bid_commercial"
    BID_EVIDENCE = "bid_evidence"
    OTHER = "other"


class DocumentReviewStatus(StrEnum):
    PENDING = "pending"
    REVIEWED = "reviewed"


class DocumentControllingStatus(StrEnum):
    NOT_CONTROLLING = "not_controlling"
    CONTROLLING = "controlling"


class DocumentRelationshipType(StrEnum):
    SUPERSEDES = "supersedes"
    AMENDS = "amends"
    CLARIFIES = "clarifies"
    INCORPORATES = "incorporates"
    REFERENCES = "references"
    REPLACES = "replaces"


class EvidenceExtractionMethod(StrEnum):
    PARSER = "parser"
    OCR = "ocr"
    HUMAN_TRANSCRIPTION = "human_transcription"
    AI_CANDIDATE = "ai_candidate"


class FindingState(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CLARIFICATION_REQUIRED = "clarification_required"
    RESOLVED = "resolved"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"
    SUPERSEDED = "superseded"


class ComplianceState(StrEnum):
    COMPLIANT_VERIFIED = "compliant_verified"
    CLAIMED_COMPLIANT = "claimed_compliant"
    PARTIALLY_EVIDENCED = "partially_evidenced"
    NON_COMPLIANT = "non_compliant"
    AMBIGUOUS = "ambiguous"
    NOT_APPLICABLE = "not_applicable"
    HUMAN_DETERMINATION_REQUIRED = "human_determination_required"


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(512))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    module_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="pre_bid")
    procurement_archetype: Mapped[str] = mapped_column(String(64), nullable=False, default="custom")
    tender_number: Mapped[str | None] = mapped_column(String(200))
    procuring_organization: Mapped[str | None] = mapped_column(String(200))
    jurisdiction: Mapped[str | None] = mapped_column(String(200))
    currency: Mapped[str | None] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_project_tenant_name"),)


class DesignBasisVersion(Base):
    __tablename__ = "design_basis_versions"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_design_basis_project_version"),
    )


class DocumentFamily(Base):
    __tablename__ = "document_families"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    family_id: Mapped[UUID | None] = mapped_column(ForeignKey("document_families.id"))
    filename: Mapped[str] = mapped_column(String(255))
    document_type: Mapped[str] = mapped_column(
        String(64), nullable=False, default=DocumentType.OTHER
    )
    volume: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(500))
    revision: Mapped[str | None] = mapped_column(String(100))
    issue_date: Mapped[date | None] = mapped_column()
    effective_date: Mapped[date | None] = mapped_column()
    tender_number: Mapped[str | None] = mapped_column(String(200))
    addendum_number: Mapped[str | None] = mapped_column(String(100))
    corrigendum_number: Mapped[str | None] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    parser_version: Mapped[str | None] = mapped_column(String(100))
    ocr_version: Mapped[str | None] = mapped_column(String(100))
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DocumentReviewStatus.PENDING
    )
    controlling_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DocumentControllingStatus.NOT_CONTROLLING
    )
    state: Mapped[str] = mapped_column(String(32), default=DocumentState.UPLOADED)
    uploaded_by: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (UniqueConstraint("project_id", "sha256", name="uq_document_project_hash"),)


class DocumentRelationship(Base):
    __tablename__ = "document_relationships"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    source_document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    target_document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(32), nullable=False)
    affected_clauses: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewer_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=DocumentReviewStatus.PENDING
    )
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "target_document_id",
            "relationship_type",
            name="uq_document_relationship",
        ),
    )


class Page(Base):
    __tablename__ = "pages"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_page_document_number"),
    )


class EvidenceSpan(Base):
    __tablename__ = "evidence_spans"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    page_id: Mapped[UUID] = mapped_column(ForeignKey("pages.id"), nullable=False)
    exact_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer)
    end_offset: Mapped[int | None] = mapped_column(Integer)
    coordinates: Mapped[dict[str, float] | None] = mapped_column(JSON)
    extraction_method: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EvidenceExtractionMethod.HUMAN_TRANSCRIPTION
    )
    extraction_version: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column()
    created_by: Mapped[UUID | None] = mapped_column(Uuid)
    verified_by: Mapped[UUID | None] = mapped_column(Uuid)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    stable_key: Mapped[str] = mapped_column(String(32), nullable=False)
    taxonomy: Mapped[str] = mapped_column(String(3), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_type: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(500))
    metric: Mapped[str | None] = mapped_column(String(200))
    comparator: Mapped[str | None] = mapped_column(String(32))
    threshold: Mapped[str | None] = mapped_column(String(200))
    minimum_value: Mapped[float | None] = mapped_column()
    maximum_value: Mapped[float | None] = mapped_column()
    unit: Mapped[str | None] = mapped_column(String(64))
    measurement_boundary: Mapped[str | None] = mapped_column(String(500))
    measurement_point: Mapped[str | None] = mapped_column(String(500))
    measurement_period: Mapped[str | None] = mapped_column(String(500))
    test_method: Mapped[str | None] = mapped_column(Text)
    mandatory: Mapped[bool | None] = mapped_column(Boolean)
    evaluation_treatment: Mapped[str] = mapped_column(
        String(32), nullable=False, default="not_specified"
    )
    evidence_required: Mapped[str | None] = mapped_column(Text)
    contractual_consequence: Mapped[str | None] = mapped_column(Text)
    responsible_party: Mapped[str | None] = mapped_column(String(200))
    applicability_condition: Mapped[str | None] = mapped_column(Text)
    applicable_start_year: Mapped[int | None] = mapped_column(Integer)
    applicable_end_year: Mapped[int | None] = mapped_column(Integer)
    materiality: Mapped[str | None] = mapped_column(String(32))
    owner_discipline: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[UUID | None] = mapped_column(Uuid)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("project_id", "stable_key", name="uq_requirement_project_key"),
    )


class RequirementEvidence(Base):
    __tablename__ = "requirement_evidence"
    requirement_id: Mapped[UUID] = mapped_column(ForeignKey("requirements.id"), primary_key=True)
    evidence_span_id: Mapped[UUID] = mapped_column(
        ForeignKey("evidence_spans.id"), primary_key=True
    )
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    requirement_id: Mapped[UUID] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    affected_objects: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    source_evidence: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default=FindingState.OPEN)
    assigned_owner: Mapped[str | None] = mapped_column(String(200))
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[UUID | None] = mapped_column(Uuid)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Clarification(Base):
    __tablename__ = "clarifications"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    finding_id: Mapped[UUID | None] = mapped_column(ForeignKey("findings.id"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str | None] = mapped_column(Text)
    proposed_wording: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    buyer_response: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApprovalRecord(Base):
    __tablename__ = "approval_records"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    object_version: Mapped[int | None] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(64))
    new_state: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Baseline(Base):
    __tablename__ = "baselines"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    frozen_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_baseline_project_version"),
    )


class FormulaCalculation(Base):
    __tablename__ = "formula_calculations"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    formula_config_id: Mapped[UUID | None] = mapped_column(ForeignKey("formula_configs.id"))
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    inputs: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    output_value: Mapped[str] = mapped_column(String(100), nullable=False)
    reproducibility_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FormulaConfig(Base):
    __tablename__ = "formula_configs"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_clause_text: Mapped[str | None] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[UUID | None] = mapped_column(Uuid)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_formula_config_project_version"),
    )


class BidderProfile(Base):
    __tablename__ = "bidder_profiles"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    legal_entity: Mapped[str] = mapped_column(String(500), nullable=False)
    parent_entity: Mapped[str | None] = mapped_column(String(500))
    consortium_members: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    oem_associations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BidComplianceMapping(Base):
    __tablename__ = "bid_compliance_mappings"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    requirement_id: Mapped[UUID] = mapped_column(ForeignKey("requirements.id"), nullable=False)
    compliance_state: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    evidence_document_id: Mapped[UUID | None] = mapped_column(ForeignKey("documents.id"))
    determined_by: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "project_id", "requirement_id", name="uq_bid_compliance_project_requirement"
        ),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    object_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Index("ix_pages_document_order", Page.document_id, Page.page_number)
Index("ix_document_families_project", DocumentFamily.project_id, DocumentFamily.created_at)
Index("ix_documents_project_family", Document.project_id, Document.family_id)
Index(
    "ix_document_relationships_project",
    DocumentRelationship.project_id,
    DocumentRelationship.created_at,
)
Index("ix_evidence_project_tenant", EvidenceSpan.project_id, EvidenceSpan.tenant_id)
Index("ix_findings_project_state", Finding.project_id, Finding.state)
Index("ix_clarifications_project_status", Clarification.project_id, Clarification.status)
Index("ix_approvals_project_created", ApprovalRecord.project_id, ApprovalRecord.created_at)
Index("ix_formula_configs_project_version", FormulaConfig.project_id, FormulaConfig.version)
Index(
    "ix_formula_calculations_config_created",
    FormulaCalculation.formula_config_id,
    FormulaCalculation.created_at,
)
Index("ix_audit_project_created", AuditEvent.project_id, AuditEvent.created_at)
