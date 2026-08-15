import csv
import hashlib
import io
import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from packages.domain.completeness import RULES, evaluate_rule_ids
from packages.domain.design_basis import DesignBasis, ModuleMode, ProcurementArchetype
from packages.domain.formulas import FormulaTemplate, evaluate_formula
from packages.domain.requirements import (
    EvidenceReference,
    RequirementKey,
    RequirementState,
    TaxonomyCode,
    can_transition,
    require_verifiable_evidence,
)
from pydantic import BaseModel, Field
from pypdf import PdfReader
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.auth import hash_password, issue_session_token, session_expiry, verify_password
from apps.api.db import Base, get_engine, get_session
from apps.api.models import (
    ApprovalRecord,
    AuditEvent,
    AuthSession,
    Baseline,
    BidComplianceMapping,
    BidderProfile,
    Clarification,
    ComplianceState,
    DesignBasisVersion,
    Document,
    DocumentFamily,
    DocumentRelationship,
    DocumentRelationshipType,
    DocumentState,
    DocumentType,
    EvidenceSpan,
    Finding,
    FindingState,
    FormulaCalculation,
    FormulaConfig,
    Membership,
    Page,
    Project,
    Requirement,
    RequirementEvidence,
    ReviewDecision,
    Tenant,
    User,
)
from apps.api.settings import get_settings

app = FastAPI(title="Fluxera BESS Intelligence Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Actor-Id", "X-Tenant-Id"],
)


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(default="UTC", max_length=64)
    module_mode: ModuleMode = ModuleMode.PRE_BID
    procurement_archetype: ProcurementArchetype = ProcurementArchetype.CUSTOM
    tender_number: str | None = Field(default=None, max_length=200)
    procuring_organization: str | None = Field(default=None, max_length=200)
    jurisdiction: str | None = Field(default=None, max_length=200)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class EvidenceInput(BaseModel):
    page_id: UUID
    exact_text: str = Field(min_length=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    verification_note: str | None = Field(default=None, max_length=10_000)


class RequirementInput(BaseModel):
    stable_key: str
    taxonomy: TaxonomyCode
    text: str = Field(min_length=1)
    evidence_span_ids: list[UUID] = Field(min_length=1)
    requirement_type: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=500)
    metric: str | None = Field(default=None, max_length=200)
    comparator: str | None = Field(default=None, max_length=32)
    threshold: str | None = Field(default=None, max_length=200)
    minimum_value: float | None = None
    maximum_value: float | None = None
    unit: str | None = Field(default=None, max_length=64)
    measurement_boundary: str | None = Field(default=None, max_length=500)
    measurement_point: str | None = Field(default=None, max_length=500)
    measurement_period: str | None = Field(default=None, max_length=500)
    test_method: str | None = Field(default=None, max_length=10_000)
    mandatory: bool | None = None
    evaluation_treatment: str = Field(default="not_specified", max_length=32)
    evidence_required: str | None = Field(default=None, max_length=10_000)
    contractual_consequence: str | None = Field(default=None, max_length=10_000)
    responsible_party: str | None = Field(default=None, max_length=200)
    applicability_condition: str | None = Field(default=None, max_length=10_000)
    applicable_start_year: int | None = Field(default=None, ge=0)
    applicable_end_year: int | None = Field(default=None, ge=0)
    materiality: str | None = Field(default=None, max_length=32)
    owner_discipline: str | None = Field(default=None, max_length=64)


class ReviewInput(BaseModel):
    decision: RequirementState
    expected_version: int = Field(ge=1)


class FindingResolutionInput(BaseModel):
    state: FindingState
    reason: str = Field(min_length=1, max_length=10_000)


class ClarificationInput(BaseModel):
    finding_id: UUID | None = None
    question: str = Field(min_length=1, max_length=10_000)
    rationale: str = Field(min_length=1, max_length=10_000)
    impact: str | None = Field(default=None, max_length=10_000)
    proposed_wording: str | None = Field(default=None, max_length=10_000)
    owner: str | None = Field(default=None, max_length=200)


class BaselineFreezeInput(BaseModel):
    reason: str = Field(min_length=1, max_length=10_000)


class FormulaEvaluationInput(BaseModel):
    template: FormulaTemplate
    inputs: dict[str, float]


class FormulaConfigInput(BaseModel):
    template: FormulaTemplate
    source_clause_text: str | None = Field(default=None, max_length=10_000)


class FormulaConfigEvaluationInput(BaseModel):
    inputs: dict[str, float]


class BidderProfileInput(BaseModel):
    legal_entity: str = Field(min_length=1, max_length=500)
    parent_entity: str | None = Field(default=None, max_length=500)


class BidComplianceInput(BaseModel):
    requirement_id: UUID
    compliance_state: ComplianceState
    rationale: str | None = Field(default=None, max_length=10_000)


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)


class BootstrapInput(LoginInput):
    organization_name: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)


class DesignBasisInput(BaseModel):
    rated_power_mw: float = Field(gt=0)
    nominal_energy_mwh: float = Field(gt=0)
    required_usable_energy_mwh: float = Field(gt=0)
    duration_hours: float = Field(gt=0)
    project_life_years: int = Field(gt=0)
    availability_target_percent: float = Field(ge=0, le=100)
    round_trip_efficiency_target_percent: float = Field(ge=0, le=100)
    cycles_per_day: float = Field(ge=0)
    use_case: str = Field(min_length=1, max_length=100)
    ac_dc_boundary: str = Field(min_length=1, max_length=200)
    response_time_seconds: float | None = Field(default=None, gt=0)
    capacity_retention_final_year: int | None = Field(default=None, gt=0)
    location: str | None = Field(default=None, max_length=500)
    jurisdiction: str | None = Field(default=None, max_length=200)
    interconnection_voltage_kv: float | None = Field(default=None, gt=0)
    delivery_point: str | None = Field(default=None, max_length=500)
    cod: str | None = Field(default=None, max_length=10)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    timezone: str | None = Field(default=None, max_length=64)
    contract_term_years: int | None = Field(default=None, gt=0)
    total_contractual_cycles: float | None = Field(default=None, ge=0)
    annual_throughput_mwh: float | None = Field(default=None, ge=0)
    maximum_cycles_per_day: float | None = Field(default=None, ge=0)
    partial_cycle_treatment: str | None = Field(default=None, max_length=500)
    soc_operating_window: str | None = Field(default=None, max_length=500)
    charge_duration_hours: float | None = Field(default=None, gt=0)
    discharge_duration_hours: float | None = Field(default=None, gt=0)
    cooling_recovery_time_hours: float | None = Field(default=None, ge=0)
    operational_window: str | None = Field(default=None, max_length=500)
    charging_energy_provider: str | None = Field(default=None, max_length=200)
    dispatch_notice: str | None = Field(default=None, max_length=500)
    rte_measurement_point: str | None = Field(default=None, max_length=500)
    rte_frequency: str | None = Field(default=None, max_length=200)
    auxiliary_consumption_treatment: str | None = Field(default=None, max_length=500)
    availability_period: str | None = Field(default=None, max_length=500)
    planned_outage_exclusion: str | None = Field(default=None, max_length=500)
    grid_outage_exclusion: str | None = Field(default=None, max_length=500)
    capacity_test_method: str | None = Field(default=None, max_length=1_000)
    capacity_retention_trajectory: dict[int, float] | None = None
    end_of_life_retention_percent: float | None = Field(default=None, ge=0, le=100)
    oversizing_allowed: bool | None = None
    augmentation_allowed: bool | None = None
    augmentation_mandatory: bool | None = None
    augmentation_payer: str | None = Field(default=None, max_length=200)
    replacement_allowed: bool | None = None
    augmentation_outage_treatment: str | None = Field(default=None, max_length=500)
    required_design_cycle_life: float | None = Field(default=None, ge=0)
    warranty_cycle_requirement: float | None = Field(default=None, ge=0)
    financial_evaluation_method: str | None = Field(default=None, max_length=200)
    reverse_auction_used: bool | None = None
    reverse_auction_parameter: str | None = Field(default=None, max_length=500)
    discount_rate_percent: float | None = Field(default=None, ge=0, le=100)
    om_term_years: int | None = Field(default=None, gt=0)
    om_escalation_percent: float | None = Field(default=None, ge=0, le=100)
    rte_price_adjustment: str | None = Field(default=None, max_length=500)
    ld_structure: str | None = Field(default=None, max_length=1_000)
    aggregate_ld_cap_percent: float | None = Field(default=None, ge=0, le=100)
    emd_amount: float | None = Field(default=None, ge=0)
    pbg_amount: float | None = Field(default=None, ge=0)
    vgf_treatment: str | None = Field(default=None, max_length=500)


class DocumentRelationshipInput(BaseModel):
    source_document_id: UUID
    target_document_id: UUID
    relationship_type: DocumentRelationshipType
    affected_clauses: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=10_000)


def actor_context(
    authorization: str | None = Header(default=None),
    x_tenant_id: UUID | None = Header(default=None),
    x_actor_id: UUID | None = Header(default=None),
    session: Session = Depends(get_session),
) -> tuple[UUID, UUID]:
    if x_tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="organization context required"
        )
    actor_id: UUID | None = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session_record = session.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > datetime.now(UTC),
            )
        )
        if session_record is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
        user = session.get(User, session_record.user_id)
        if user is None or user.disabled_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="user is unavailable"
            )
        actor_id = user.id
    elif get_settings().environment == "local" and get_settings().allow_development_identity:
        actor_id = x_actor_id
    if actor_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )
    if (
        session.scalar(
            select(Membership).where(
                Membership.tenant_id == x_tenant_id, Membership.user_id == actor_id
            )
        )
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant membership required"
        )
    return x_tenant_id, actor_id


def ensure_schema() -> None:
    if get_settings().environment == "local":
        Base.metadata.create_all(get_engine())


def audit(
    session: Session,
    tenant_id: UUID,
    project_id: UUID,
    actor_id: UUID,
    action: str,
    object_type: str,
    object_id: UUID,
) -> None:
    session.add(
        AuditEvent(
            tenant_id=tenant_id,
            project_id=project_id,
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            created_at=datetime.now(UTC),
        )
    )


def project_data(project: Project) -> dict[str, object]:
    return {
        "id": project.id,
        "tenant_id": project.tenant_id,
        "name": project.name,
        "timezone": project.timezone,
        "module_mode": project.module_mode,
        "procurement_archetype": project.procurement_archetype,
        "tender_number": project.tender_number,
        "procuring_organization": project.procuring_organization,
        "jurisdiction": project.jurisdiction,
        "currency": project.currency,
        "status": project.status,
    }


def design_basis_data(basis: DesignBasisVersion) -> dict[str, object]:
    return {
        "id": basis.id,
        "version": basis.version,
        "status": basis.status,
        "data": basis.data,
        "created_at": basis.created_at,
        "approved_at": basis.approved_at,
    }


def document_data(document: Document) -> dict[str, object]:
    return {
        "id": document.id,
        "project_id": document.project_id,
        "family_id": document.family_id,
        "filename": document.filename,
        "document_type": document.document_type,
        "volume": document.volume,
        "title": document.title,
        "revision": document.revision,
        "issue_date": document.issue_date,
        "effective_date": document.effective_date,
        "tender_number": document.tender_number,
        "addendum_number": document.addendum_number,
        "corrigendum_number": document.corrigendum_number,
        "sha256": document.sha256,
        "state": document.state,
        "byte_size": document.byte_size,
        "parser_version": document.parser_version,
        "ocr_version": document.ocr_version,
        "page_count": document.page_count,
        "review_status": document.review_status,
        "controlling_status": document.controlling_status,
        "created_at": document.created_at,
    }


def page_data(page: Page) -> dict[str, object]:
    return {
        "id": page.id,
        "document_id": page.document_id,
        "page_number": page.page_number,
        "text": page.text,
    }


def evidence_data(span: EvidenceSpan) -> dict[str, object]:
    return {
        "id": span.id,
        "page_id": span.page_id,
        "exact_text": span.exact_text,
        "start_offset": span.start_offset,
        "end_offset": span.end_offset,
        "extraction_method": span.extraction_method,
        "confidence": span.confidence,
        "verified_at": span.verified_at,
        "verification_note": span.verification_note,
    }


def requirement_data(requirement: Requirement) -> dict[str, object]:
    return {
        "id": requirement.id,
        "project_id": requirement.project_id,
        "stable_key": requirement.stable_key,
        "taxonomy": requirement.taxonomy,
        "text": requirement.text,
        "requirement_type": requirement.requirement_type,
        "title": requirement.title,
        "metric": requirement.metric,
        "comparator": requirement.comparator,
        "threshold": requirement.threshold,
        "minimum_value": requirement.minimum_value,
        "maximum_value": requirement.maximum_value,
        "unit": requirement.unit,
        "measurement_boundary": requirement.measurement_boundary,
        "measurement_point": requirement.measurement_point,
        "measurement_period": requirement.measurement_period,
        "test_method": requirement.test_method,
        "mandatory": requirement.mandatory,
        "evaluation_treatment": requirement.evaluation_treatment,
        "materiality": requirement.materiality,
        "owner_discipline": requirement.owner_discipline,
        "state": requirement.state,
        "version": requirement.version,
    }


def finding_data(finding: Finding) -> dict[str, object]:
    return {
        "id": finding.id,
        "rule_id": finding.rule_id,
        "rule_version": finding.rule_version,
        "type": finding.finding_type,
        "severity": finding.severity,
        "title": finding.title,
        "explanation": finding.explanation,
        "affected_objects": finding.affected_objects,
        "source_evidence": finding.source_evidence,
        "suggested_action": finding.suggested_action,
        "state": finding.state,
        "assigned_owner": finding.assigned_owner,
        "resolution": finding.resolution,
        "resolved_at": finding.resolved_at,
        "created_at": finding.created_at,
    }


def clarification_data(clarification: Clarification) -> dict[str, object]:
    return {
        "id": clarification.id,
        "finding_id": clarification.finding_id,
        "question": clarification.question,
        "rationale": clarification.rationale,
        "impact": clarification.impact,
        "proposed_wording": clarification.proposed_wording,
        "owner": clarification.owner,
        "status": clarification.status,
        "buyer_response": clarification.buyer_response,
        "created_at": clarification.created_at,
    }


def baseline_data(baseline: Baseline) -> dict[str, object]:
    return {
        "id": baseline.id,
        "version": baseline.version,
        "content_hash": baseline.content_hash,
        "data": baseline.data,
        "frozen_at": baseline.frozen_at,
    }


def bidder_profile_data(profile: BidderProfile) -> dict[str, object]:
    return {
        "id": profile.id,
        "legal_entity": profile.legal_entity,
        "parent_entity": profile.parent_entity,
    }


def bid_compliance_data(mapping: BidComplianceMapping) -> dict[str, object]:
    return {
        "id": mapping.id,
        "requirement_id": mapping.requirement_id,
        "compliance_state": mapping.compliance_state,
        "rationale": mapping.rationale,
    }


def formula_calculation_data(calculation: FormulaCalculation) -> dict[str, object]:
    return {
        "id": calculation.id,
        "formula_config_id": calculation.formula_config_id,
        "template": calculation.template,
        "inputs": calculation.inputs,
        "output_value": calculation.output_value,
        "reproducibility_hash": calculation.reproducibility_hash,
        "created_at": calculation.created_at,
    }


def formula_config_data(
    config: FormulaConfig, calculations: list[FormulaCalculation]
) -> dict[str, object]:
    return {
        "id": config.id,
        "template": config.template,
        "version": config.version,
        "source_clause_text": config.source_clause_text,
        "approved": config.approved,
        "approved_by": config.approved_by,
        "approved_at": config.approved_at,
        "created_at": config.created_at,
        "calculations": [formula_calculation_data(calculation) for calculation in calculations],
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    return {"status": "ready"}


def session_response(session: Session, user: User) -> dict[str, object]:
    token, token_hash = issue_session_token()
    session.add(
        AuthSession(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=session_expiry(get_settings().session_ttl_minutes),
            created_at=datetime.now(UTC),
        )
    )
    session.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": get_settings().session_ttl_minutes * 60,
        "user": {"id": user.id, "email": user.email, "display_name": user.display_name},
    }


@app.post("/auth/bootstrap", status_code=201, tags=["auth"])
def bootstrap_local_account(
    payload: BootstrapInput, session: Session = Depends(get_session)
) -> dict[str, object]:
    ensure_schema()
    if get_settings().environment != "local":
        raise HTTPException(status_code=404, detail="not found")
    if session.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="email already exists")
    user = User(
        email=payload.email.lower(),
        display_name=payload.display_name,
        password_hash=hash_password(payload.password),
    )
    tenant = Tenant(name=payload.organization_name)
    session.add_all([user, tenant])
    session.flush()
    session.add(Membership(tenant_id=tenant.id, user_id=user.id, role="organization_owner"))
    session.commit()
    result = session_response(session, user)
    result["organization"] = {"id": tenant.id, "name": tenant.name, "role": "organization_owner"}
    return result


@app.post("/auth/login", tags=["auth"])
def login(payload: LoginInput, session: Session = Depends(get_session)) -> dict[str, object]:
    user = session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or user.disabled_at is not None or user.password_hash is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    return session_response(session, user)


@app.post("/auth/logout", status_code=204, tags=["auth"])
def logout(
    authorization: str | None = Header(default=None), session: Session = Depends(get_session)
) -> None:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required"
        )
    token_hash = hashlib.sha256(authorization.removeprefix("Bearer ").encode()).hexdigest()
    session_record = session.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if session_record is not None and session_record.revoked_at is None:
        session_record.revoked_at = datetime.now(UTC)
        session.commit()


@app.post("/tenants", status_code=201, tags=["projects"])
def create_tenant(
    name: str,
    x_actor_id: UUID | None = Header(default=None),
    session: Session = Depends(get_session),
) -> dict[str, UUID | str]:
    ensure_schema()
    if x_actor_id is None:
        raise HTTPException(status_code=401, detail="actor context required")
    tenant = Tenant(name=name)
    actor_id = x_actor_id
    user = session.get(User, actor_id) or User(
        id=actor_id, email=f"bootstrap-{actor_id}@local.invalid", display_name="Local administrator"
    )
    session.add(user)
    session.add(tenant)
    session.flush()
    session.add(Membership(tenant_id=tenant.id, user_id=actor_id, role="owner"))
    session.commit()
    return {"id": tenant.id, "name": tenant.name}


@app.post("/projects", status_code=201, response_model=None, tags=["projects"])
def create_project(
    payload: ProjectInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    ensure_schema()
    tenant_id, actor_id = context
    if session.get(Tenant, tenant_id) is None:
        raise HTTPException(404, "tenant not found")
    project = Project(
        tenant_id=tenant_id,
        name=payload.name,
        timezone=payload.timezone,
        module_mode=payload.module_mode,
        procurement_archetype=payload.procurement_archetype,
        tender_number=payload.tender_number,
        procuring_organization=payload.procuring_organization,
        jurisdiction=payload.jurisdiction,
        currency=payload.currency,
    )
    session.add(project)
    session.flush()
    audit(session, tenant_id, project.id, actor_id, "project.created", "project", project.id)
    session.commit()
    return project_data(project)


@app.get("/projects", response_model=None, tags=["projects"])
def list_projects(
    context: tuple[UUID, UUID] = Depends(actor_context), session: Session = Depends(get_session)
) -> list[dict[str, object]]:
    tenant_id, _ = context
    return [
        project_data(project)
        for project in session.scalars(
            select(Project).where(Project.tenant_id == tenant_id).order_by(Project.name)
        )
    ]


@app.get("/projects/{project_id}/design-basis", response_model=None, tags=["design-basis"])
def get_design_basis(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object] | None:
    tenant_id, _ = context
    basis = session.scalar(
        select(DesignBasisVersion)
        .where(
            DesignBasisVersion.project_id == project_id, DesignBasisVersion.tenant_id == tenant_id
        )
        .order_by(DesignBasisVersion.version.desc())
    )
    return design_basis_data(basis) if basis else None


@app.post(
    "/projects/{project_id}/design-basis",
    status_code=201,
    response_model=None,
    tags=["design-basis"],
)
def create_design_basis(
    project_id: UUID,
    payload: DesignBasisInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    if (
        session.scalar(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        is None
    ):
        raise HTTPException(404, "project not found")
    try:
        DesignBasis(**payload.model_dump()).validate()
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    latest = session.scalar(
        select(DesignBasisVersion)
        .where(DesignBasisVersion.project_id == project_id)
        .order_by(DesignBasisVersion.version.desc())
    )
    basis = DesignBasisVersion(
        tenant_id=tenant_id,
        project_id=project_id,
        version=(latest.version + 1) if latest else 1,
        status="draft",
        data=payload.model_dump(),
        created_by=actor_id,
        created_at=datetime.now(UTC),
    )
    session.add(basis)
    session.flush()
    audit(
        session, tenant_id, project_id, actor_id, "design_basis.created", "design_basis", basis.id
    )
    session.commit()
    return design_basis_data(basis)


@app.post(
    "/projects/{project_id}/design-basis/{basis_id}/approve",
    response_model=None,
    tags=["design-basis"],
)
def approve_design_basis(
    project_id: UUID,
    basis_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    basis = session.scalar(
        select(DesignBasisVersion).where(
            DesignBasisVersion.id == basis_id,
            DesignBasisVersion.project_id == project_id,
            DesignBasisVersion.tenant_id == tenant_id,
        )
    )
    if basis is None:
        raise HTTPException(404, "design basis not found")
    if basis.status != "draft":
        raise HTTPException(409, "only a draft design basis can be approved")
    basis.status = "approved"
    basis.approved_by = actor_id
    basis.approved_at = datetime.now(UTC)
    audit(
        session, tenant_id, project_id, actor_id, "design_basis.approved", "design_basis", basis.id
    )
    session.commit()
    return design_basis_data(basis)


@app.post(
    "/projects/{project_id}/documents", status_code=201, response_model=None, tags=["documents"]
)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(default=DocumentType.OTHER),
    volume: str | None = Form(default=None, max_length=100),
    title: str | None = Form(default=None, max_length=500),
    revision: str | None = Form(default=None, max_length=100),
    issue_date: date | None = Form(default=None),
    effective_date: date | None = Form(default=None),
    tender_number: str | None = Form(default=None, max_length=200),
    addendum_number: str | None = Form(default=None, max_length=100),
    corrigendum_number: str | None = Form(default=None, max_length=100),
    family_id: UUID | None = Form(default=None),
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    ensure_schema()
    tenant_id, actor_id = context
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    )
    if project is None:
        raise HTTPException(404, "project not found")
    if file.content_type != "application/pdf":
        raise HTTPException(415, "only application/pdf is accepted")
    content = await file.read(get_settings().max_upload_bytes + 1)
    if len(content) > get_settings().max_upload_bytes or not content.startswith(b"%PDF-"):
        raise HTTPException(400, "invalid or oversized PDF")
    digest = hashlib.sha256(content).hexdigest()
    existing = session.scalar(
        select(Document).where(Document.project_id == project_id, Document.sha256 == digest)
    )
    if existing is not None:
        return document_data(existing)
    if (
        family_id is not None
        and session.scalar(
            select(DocumentFamily).where(
                DocumentFamily.id == family_id,
                DocumentFamily.project_id == project_id,
                DocumentFamily.tenant_id == tenant_id,
            )
        )
        is None
    ):
        raise HTTPException(422, "document family must belong to this project")
    try:
        reader = PdfReader(io.BytesIO(content))
        if len(reader.pages) > get_settings().max_pdf_pages:
            raise HTTPException(400, "PDF page limit exceeded")
        pages = [(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(422, "PDF parsing failed") from error
    object_key = f"{tenant_id}/{project_id}/{digest}.pdf"
    path = Path(get_settings().storage_dir) / object_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    document = Document(
        tenant_id=tenant_id,
        project_id=project_id,
        family_id=family_id,
        filename=file.filename or "upload.pdf",
        document_type=document_type,
        volume=volume,
        title=title,
        revision=revision,
        issue_date=issue_date,
        effective_date=effective_date,
        tender_number=tender_number,
        addendum_number=addendum_number,
        corrigendum_number=corrigendum_number,
        sha256=digest,
        object_key=object_key,
        mime_type="application/pdf",
        byte_size=len(content),
        parser_version="pypdf-5.4.0",
        page_count=len(pages),
        state=DocumentState.REVIEW_READY,
        uploaded_by=actor_id,
        created_at=datetime.now(UTC),
    )
    session.add(document)
    session.flush()
    for page_number, text in pages:
        session.add(
            Page(
                document_id=document.id,
                page_number=page_number,
                text=text,
                created_at=datetime.now(UTC),
            )
        )
    audit(session, tenant_id, project_id, actor_id, "document.uploaded", "document", document.id)
    session.commit()
    return document_data(document)


@app.get("/projects/{project_id}/documents", response_model=None, tags=["documents"])
def list_documents(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    return [
        document_data(document)
        for document in session.scalars(
            select(Document)
            .where(Document.project_id == project_id, Document.tenant_id == tenant_id)
            .order_by(Document.created_at, Document.filename)
        )
    ]


@app.post(
    "/projects/{project_id}/document-relationships",
    status_code=201,
    response_model=None,
    tags=["documents"],
)
def create_document_relationship(
    project_id: UUID,
    payload: DocumentRelationshipInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    if payload.source_document_id == payload.target_document_id:
        raise HTTPException(422, "a document cannot relate to itself")
    documents = list(
        session.scalars(
            select(Document).where(
                Document.id.in_([payload.source_document_id, payload.target_document_id]),
                Document.project_id == project_id,
                Document.tenant_id == tenant_id,
            )
        )
    )
    if len(documents) != 2:
        raise HTTPException(422, "both documents must belong to this project")
    relationship = DocumentRelationship(
        tenant_id=tenant_id,
        project_id=project_id,
        source_document_id=payload.source_document_id,
        target_document_id=payload.target_document_id,
        relationship_type=payload.relationship_type,
        affected_clauses=payload.affected_clauses,
        reason=payload.reason,
        created_by=actor_id,
        created_at=datetime.now(UTC),
    )
    session.add(relationship)
    session.flush()
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "document.relationship_created",
        "document_relationship",
        relationship.id,
    )
    session.commit()
    return document_relationship_data(relationship)


def document_relationship_data(relationship: DocumentRelationship) -> dict[str, object]:
    return {
        "id": relationship.id,
        "source_document_id": relationship.source_document_id,
        "target_document_id": relationship.target_document_id,
        "relationship_type": relationship.relationship_type,
        "affected_clauses": relationship.affected_clauses,
        "reason": relationship.reason,
        "reviewer_status": relationship.reviewer_status,
        "created_at": relationship.created_at,
    }


@app.get(
    "/projects/{project_id}/document-relationships/{relationship_id}/impact",
    response_model=None,
    tags=["documents"],
)
def document_relationship_impact(
    project_id: UUID,
    relationship_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, _ = context
    relationship = session.scalar(
        select(DocumentRelationship).where(
            DocumentRelationship.id == relationship_id,
            DocumentRelationship.project_id == project_id,
            DocumentRelationship.tenant_id == tenant_id,
        )
    )
    if relationship is None:
        raise HTTPException(404, "document relationship not found")
    impacted = session.execute(
        select(Requirement.id, Requirement.stable_key, Requirement.state)
        .join(RequirementEvidence, RequirementEvidence.requirement_id == Requirement.id)
        .join(EvidenceSpan, EvidenceSpan.id == RequirementEvidence.evidence_span_id)
        .join(Page, Page.id == EvidenceSpan.page_id)
        .where(
            Requirement.project_id == project_id,
            Requirement.tenant_id == tenant_id,
            Page.document_id == relationship.target_document_id,
        )
        .distinct()
        .order_by(Requirement.stable_key)
    )
    return {
        "relationship": document_relationship_data(relationship),
        "requires_re_review": relationship.relationship_type
        in {
            DocumentRelationshipType.SUPERSEDES,
            DocumentRelationshipType.AMENDS,
            DocumentRelationshipType.REPLACES,
        },
        "impacted_requirements": [
            {"id": requirement_id, "stable_key": stable_key, "state": requirement_state}
            for requirement_id, stable_key, requirement_state in impacted
        ],
    }


@app.get("/projects/{project_id}/pages", response_model=None, tags=["evidence"])
def list_pages(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    if (
        session.scalar(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        is None
    ):
        raise HTTPException(404, "project not found")
    return [
        page_data(page)
        for page in session.scalars(
            select(Page)
            .join(Document)
            .where(Document.project_id == project_id, Document.tenant_id == tenant_id)
            .order_by(Page.document_id, Page.page_number)
        )
    ]


@app.post(
    "/projects/{project_id}/evidence", status_code=201, response_model=None, tags=["evidence"]
)
def create_evidence(
    project_id: UUID,
    payload: EvidenceInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    page = session.scalar(
        select(Page)
        .join(Document)
        .where(
            Page.id == payload.page_id,
            Document.project_id == project_id,
            Document.tenant_id == tenant_id,
        )
    )
    if page is None or (payload.exact_text not in page.text and page.text):
        raise HTTPException(422, "evidence text must occur on the selected page")
    span = EvidenceSpan(
        tenant_id=tenant_id,
        project_id=project_id,
        page_id=page.id,
        exact_text=payload.exact_text,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        extraction_method="human_transcription",
        created_by=actor_id,
        created_at=datetime.now(UTC),
    )
    session.add(span)
    session.flush()
    audit(session, tenant_id, project_id, actor_id, "evidence.created", "evidence_span", span.id)
    session.commit()
    return evidence_data(span)


@app.post(
    "/projects/{project_id}/requirements/{requirement_id}/evidence/{evidence_span_id}/verify",
    response_model=None,
    tags=["evidence"],
)
def verify_evidence(
    project_id: UUID,
    requirement_id: UUID,
    evidence_span_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    link = session.scalar(
        select(RequirementEvidence)
        .join(Requirement)
        .join(EvidenceSpan, EvidenceSpan.id == RequirementEvidence.evidence_span_id)
        .where(
            RequirementEvidence.requirement_id == requirement_id,
            RequirementEvidence.evidence_span_id == evidence_span_id,
            Requirement.project_id == project_id,
            Requirement.tenant_id == tenant_id,
            EvidenceSpan.project_id == project_id,
            EvidenceSpan.tenant_id == tenant_id,
        )
    )
    if link is None:
        raise HTTPException(404, "requirement evidence not found")
    link.verified = True
    span = session.get(EvidenceSpan, evidence_span_id)
    if span is not None:
        span.verified_by = actor_id
        span.verified_at = datetime.now(UTC)
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "evidence.verified",
        "evidence_span",
        evidence_span_id,
    )
    session.commit()
    return {
        "requirement_id": requirement_id,
        "evidence_span_id": evidence_span_id,
        "verified": True,
    }


@app.post(
    "/projects/{project_id}/requirements",
    status_code=201,
    response_model=None,
    tags=["requirements"],
)
def create_requirement(
    project_id: UUID,
    payload: RequirementInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    try:
        RequirementKey(payload.stable_key)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    evidence = list(
        session.scalars(
            select(EvidenceSpan).where(
                EvidenceSpan.id.in_(payload.evidence_span_ids),
                EvidenceSpan.project_id == project_id,
                EvidenceSpan.tenant_id == tenant_id,
            )
        )
    )
    if len(evidence) != len(set(payload.evidence_span_ids)):
        raise HTTPException(422, "all evidence must belong to this project")
    requirement = Requirement(
        tenant_id=tenant_id,
        project_id=project_id,
        stable_key=payload.stable_key,
        taxonomy=payload.taxonomy,
        text=payload.text,
        requirement_type=payload.requirement_type,
        title=payload.title,
        metric=payload.metric,
        comparator=payload.comparator,
        threshold=payload.threshold,
        minimum_value=payload.minimum_value,
        maximum_value=payload.maximum_value,
        unit=payload.unit,
        measurement_boundary=payload.measurement_boundary,
        measurement_point=payload.measurement_point,
        measurement_period=payload.measurement_period,
        test_method=payload.test_method,
        mandatory=payload.mandatory,
        evaluation_treatment=payload.evaluation_treatment,
        evidence_required=payload.evidence_required,
        contractual_consequence=payload.contractual_consequence,
        responsible_party=payload.responsible_party,
        applicability_condition=payload.applicability_condition,
        applicable_start_year=payload.applicable_start_year,
        applicable_end_year=payload.applicable_end_year,
        materiality=payload.materiality,
        owner_discipline=payload.owner_discipline,
        created_by=actor_id,
        created_at=datetime.now(UTC),
        state=RequirementState.PROPOSED,
        version=1,
    )
    session.add(requirement)
    session.flush()
    for span in evidence:
        session.add(
            RequirementEvidence(
                requirement_id=requirement.id, evidence_span_id=span.id, verified=False
            )
        )
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "requirement.created",
        "requirement",
        requirement.id,
    )
    session.commit()
    return requirement_data(requirement)


@app.get("/projects/{project_id}/requirements", response_model=None, tags=["requirements"])
def list_requirements(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    return [
        requirement_data(requirement)
        for requirement in session.scalars(
            select(Requirement)
            .where(Requirement.project_id == project_id, Requirement.tenant_id == tenant_id)
            .order_by(Requirement.stable_key)
        )
    ]


def bid_intelligence_project(project_id: UUID, tenant_id: UUID, session: Session) -> Project:
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    )
    if project is None:
        raise HTTPException(404, "project not found")
    if project.module_mode != ModuleMode.BID_INTELLIGENCE:
        raise HTTPException(409, "Bid Intelligence workflow requires a Bid Intelligence project")
    return project


@app.post("/projects/{project_id}/bidder-profile", status_code=201, tags=["bid-intelligence"])
def create_bidder_profile(
    project_id: UUID,
    payload: BidderProfileInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    bid_intelligence_project(project_id, tenant_id, session)
    profile = BidderProfile(
        tenant_id=tenant_id,
        project_id=project_id,
        legal_entity=payload.legal_entity,
        parent_entity=payload.parent_entity,
        consortium_members=[],
        oem_associations=[],
        created_by=actor_id,
        created_at=datetime.now(UTC),
    )
    session.add(profile)
    session.flush()
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "bidder_profile.created",
        "bidder_profile",
        profile.id,
    )
    session.commit()
    return bidder_profile_data(profile)


@app.post("/projects/{project_id}/bid-compliance", status_code=201, tags=["bid-intelligence"])
def create_bid_compliance_mapping(
    project_id: UUID,
    payload: BidComplianceInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    bid_intelligence_project(project_id, tenant_id, session)
    requirement = session.scalar(
        select(Requirement).where(
            Requirement.id == payload.requirement_id,
            Requirement.project_id == project_id,
            Requirement.tenant_id == tenant_id,
        )
    )
    if requirement is None:
        raise HTTPException(422, "requirement must belong to this project")
    mapping = BidComplianceMapping(
        tenant_id=tenant_id,
        project_id=project_id,
        requirement_id=requirement.id,
        compliance_state=payload.compliance_state,
        rationale=payload.rationale,
        determined_by=actor_id,
        created_at=datetime.now(UTC),
    )
    session.add(mapping)
    session.flush()
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "bid_compliance.created",
        "bid_compliance",
        mapping.id,
    )
    session.commit()
    return bid_compliance_data(mapping)


@app.get("/projects/{project_id}/requirements/detailed", response_model=None, tags=["requirements"])
def list_detailed_requirements(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    requirements = session.scalars(
        select(Requirement)
        .where(Requirement.project_id == project_id, Requirement.tenant_id == tenant_id)
        .order_by(Requirement.stable_key)
    )
    result: list[dict[str, object]] = []
    for requirement in requirements:
        evidence_links = session.execute(
            select(RequirementEvidence, EvidenceSpan, Page)
            .join(EvidenceSpan, EvidenceSpan.id == RequirementEvidence.evidence_span_id)
            .join(Page, Page.id == EvidenceSpan.page_id)
            .where(RequirementEvidence.requirement_id == requirement.id)
            .order_by(Page.page_number, EvidenceSpan.id)
        )
        evidence = [
            {
                "id": span.id,
                "page_number": page.page_number,
                "exact_text": span.exact_text,
                "verified": link.verified,
            }
            for link, span, page in evidence_links
        ]
        result.append({**requirement_data(requirement), "evidence": evidence})
    return result


@app.get("/projects/{project_id}/pre-bid-report", response_model=None, tags=["reports"])
def pre_bid_report(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, _ = context
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    )
    if project is None:
        raise HTTPException(404, "project not found")
    documents = list(
        session.scalars(
            select(Document)
            .where(Document.project_id == project_id, Document.tenant_id == tenant_id)
            .order_by(Document.created_at, Document.filename)
        )
    )
    pages = list(
        session.scalars(
            select(Page)
            .join(Document)
            .where(Document.project_id == project_id, Document.tenant_id == tenant_id)
        )
    )
    requirements = list(
        session.scalars(
            select(Requirement)
            .where(Requirement.project_id == project_id, Requirement.tenant_id == tenant_id)
            .order_by(Requirement.stable_key)
        )
    )
    evidence = list(
        session.scalars(
            select(EvidenceSpan).where(
                EvidenceSpan.project_id == project_id, EvidenceSpan.tenant_id == tenant_id
            )
        )
    )
    verified_evidence_count = len(
        list(
            session.scalars(
                select(RequirementEvidence)
                .join(Requirement)
                .where(
                    Requirement.project_id == project_id,
                    Requirement.tenant_id == tenant_id,
                    RequirementEvidence.verified.is_(True),
                )
            )
        )
    )
    state_counts = {state.value: 0 for state in RequirementState}
    taxonomy_counts: dict[str, int] = {}
    for requirement in requirements:
        state_counts[requirement.state] = state_counts.get(requirement.state, 0) + 1
        taxonomy_counts[requirement.taxonomy] = taxonomy_counts.get(requirement.taxonomy, 0) + 1
    completed = state_counts[RequirementState.VERIFIED] + state_counts[RequirementState.REJECTED]
    review_progress = round(completed / len(requirements) * 100) if requirements else 0
    return {
        "project_id": project_id,
        "project_name": project.name,
        "source_documents": [
            {
                "id": document.id,
                "filename": document.filename,
                "sha256": document.sha256,
                "state": document.state,
                "byte_size": document.byte_size,
                "created_at": document.created_at,
                "page_count": sum(page.document_id == document.id for page in pages),
            }
            for document in documents
        ],
        "document_count": len(documents),
        "pages_extracted": len(pages),
        "total_bytes": sum(document.byte_size for document in documents),
        "requirements_created": len(requirements),
        "requirements_by_state": state_counts,
        "requirements_by_taxonomy": taxonomy_counts,
        "evidence_spans_count": len(evidence),
        "verified_evidence_count": verified_evidence_count,
        "review_progress_percent": review_progress,
        "ready_for_export": state_counts[RequirementState.VERIFIED] > 0,
        "report_status": "review_ready" if documents else "awaiting_documents",
        "intelligence_notice": (
            "Document coverage is complete only for uploaded sources. Requirement extraction and "
            "compliance conclusions require authorized human review."
        ),
    }


@app.get("/projects/{project_id}/pre-bid-assurance-report", response_model=None, tags=["reports"])
def pre_bid_assurance_report(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, _ = context
    project = session.scalar(
        select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
    )
    if project is None:
        raise HTTPException(404, "project not found")
    basis = session.scalar(
        select(DesignBasisVersion)
        .where(
            DesignBasisVersion.project_id == project_id,
            DesignBasisVersion.tenant_id == tenant_id,
            DesignBasisVersion.status == "approved",
        )
        .order_by(DesignBasisVersion.version.desc())
    )
    documents = list(
        session.scalars(
            select(Document)
            .where(Document.project_id == project_id, Document.tenant_id == tenant_id)
            .order_by(Document.created_at)
        )
    )
    requirements = list(
        session.scalars(
            select(Requirement).where(
                Requirement.project_id == project_id, Requirement.tenant_id == tenant_id
            )
        )
    )
    findings = list(
        session.scalars(
            select(Finding)
            .where(Finding.project_id == project_id, Finding.tenant_id == tenant_id)
            .order_by(Finding.created_at)
        )
    )
    clarifications = list(
        session.scalars(
            select(Clarification).where(
                Clarification.project_id == project_id, Clarification.tenant_id == tenant_id
            )
        )
    )
    baselines = list(
        session.scalars(
            select(Baseline)
            .where(Baseline.project_id == project_id, Baseline.tenant_id == tenant_id)
            .order_by(Baseline.version.desc())
        )
    )
    return {
        "report_type": "pre_bid_assurance",
        "project": project_data(project),
        "approved_design_basis": design_basis_data(basis) if basis else None,
        "document_inventory": [document_data(item) for item in documents],
        "requirement_coverage": {
            "total": len(requirements),
            "verified": sum(item.state == RequirementState.VERIFIED for item in requirements),
        },
        "findings": [finding_data(item) for item in findings],
        "clarifications": [clarification_data(item) for item in clarifications],
        "baseline": baseline_data(baselines[0]) if baselines else None,
        "limitations": [
            "This report does not make a procurement decision or award recommendation.",
            (
                "Formula Lab outputs remain internal scenarios unless separately approved "
                "under tender policy."
            ),
        ],
    }


@app.get("/projects/{project_id}/completeness-findings", response_model=None, tags=["findings"])
def completeness_findings(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    basis = session.scalar(
        select(DesignBasisVersion)
        .where(
            DesignBasisVersion.project_id == project_id,
            DesignBasisVersion.tenant_id == tenant_id,
            DesignBasisVersion.status == "approved",
        )
        .order_by(DesignBasisVersion.version.desc())
    )
    if basis is None:
        raise HTTPException(
            409, "an approved Design Basis is required before completeness analysis"
        )
    requirements = session.scalars(
        select(Requirement).where(
            Requirement.project_id == project_id,
            Requirement.tenant_id == tenant_id,
            Requirement.state == RequirementState.VERIFIED,
        )
    )
    verified_taxonomies = {requirement.taxonomy for requirement in requirements}
    missing_rule_ids = set(
        evaluate_rule_ids(
            project_life_years=int(str(basis.data["project_life_years"])),
            use_case=str(basis.data["use_case"]),
            verified_taxonomies=verified_taxonomies,
        )
    )
    return [
        {
            "rule_id": rule.rule_id,
            "rule_version": rule.version,
            "type": "missing_requirement",
            "severity": rule.severity,
            "status": "open",
            "why_applies": rule.explanation,
            "searched_taxonomy": rule.taxonomy,
            "evidence_found": False,
            "suggested_action": rule.suggested_action,
        }
        for rule in RULES
        if rule.rule_id in missing_rule_ids
    ]


@app.get("/projects/{project_id}/findings", response_model=None, tags=["findings"])
def list_findings(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    return [
        finding_data(finding)
        for finding in session.scalars(
            select(Finding)
            .where(Finding.project_id == project_id, Finding.tenant_id == tenant_id)
            .order_by(Finding.state, Finding.severity.desc(), Finding.created_at)
        )
    ]


@app.post("/projects/{project_id}/findings/run", response_model=None, tags=["findings"])
def run_completeness_rules(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, actor_id = context
    basis = session.scalar(
        select(DesignBasisVersion)
        .where(
            DesignBasisVersion.project_id == project_id,
            DesignBasisVersion.tenant_id == tenant_id,
            DesignBasisVersion.status == "approved",
        )
        .order_by(DesignBasisVersion.version.desc())
    )
    if basis is None:
        raise HTTPException(
            409, "an approved Design Basis is required before completeness analysis"
        )
    requirements = session.scalars(
        select(Requirement).where(
            Requirement.project_id == project_id,
            Requirement.tenant_id == tenant_id,
            Requirement.state == RequirementState.VERIFIED,
        )
    )
    missing_rule_ids = set(
        evaluate_rule_ids(
            project_life_years=int(str(basis.data["project_life_years"])),
            use_case=str(basis.data["use_case"]),
            verified_taxonomies={requirement.taxonomy for requirement in requirements},
        )
    )
    existing_open = {
        (finding.rule_id, finding.rule_version)
        for finding in session.scalars(
            select(Finding).where(
                Finding.project_id == project_id,
                Finding.tenant_id == tenant_id,
                Finding.state == FindingState.OPEN,
            )
        )
    }
    for rule in RULES:
        if rule.rule_id not in missing_rule_ids or (rule.rule_id, rule.version) in existing_open:
            continue
        finding = Finding(
            tenant_id=tenant_id,
            project_id=project_id,
            rule_id=rule.rule_id,
            rule_version=rule.version,
            finding_type="missing_requirement",
            severity=rule.severity,
            title=rule.rule_id.replace("_", " ").title(),
            explanation=rule.explanation,
            affected_objects=[{"type": "design_basis", "id": str(basis.id)}],
            source_evidence=[],
            suggested_action=rule.suggested_action,
            state=FindingState.OPEN,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(finding)
        session.flush()
        audit(session, tenant_id, project_id, actor_id, "finding.created", "finding", finding.id)
    session.commit()
    return list_findings(project_id, context, session)


@app.post(
    "/projects/{project_id}/findings/{finding_id}/resolve",
    response_model=None,
    tags=["findings"],
)
def resolve_finding(
    project_id: UUID,
    finding_id: UUID,
    payload: FindingResolutionInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    if payload.state not in {
        FindingState.RESOLVED,
        FindingState.ACCEPTED_RISK,
        FindingState.FALSE_POSITIVE,
    }:
        raise HTTPException(422, "only a terminal finding state can resolve a finding")
    finding = session.scalar(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.project_id == project_id,
            Finding.tenant_id == tenant_id,
        )
    )
    if finding is None:
        raise HTTPException(404, "finding not found")
    if finding.state != FindingState.OPEN:
        raise HTTPException(409, "only an open finding can be resolved")
    finding.state = payload.state
    finding.resolution = payload.reason
    finding.resolved_by = actor_id
    finding.resolved_at = datetime.now(UTC)
    finding.updated_at = datetime.now(UTC)
    audit(session, tenant_id, project_id, actor_id, "finding.resolved", "finding", finding.id)
    session.commit()
    return finding_data(finding)


@app.post(
    "/projects/{project_id}/clarifications",
    status_code=201,
    response_model=None,
    tags=["clarifications"],
)
def create_clarification(
    project_id: UUID,
    payload: ClarificationInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    if (
        payload.finding_id is not None
        and session.scalar(
            select(Finding).where(
                Finding.id == payload.finding_id,
                Finding.project_id == project_id,
                Finding.tenant_id == tenant_id,
            )
        )
        is None
    ):
        raise HTTPException(422, "linked finding must belong to this project")
    clarification = Clarification(
        tenant_id=tenant_id,
        project_id=project_id,
        finding_id=payload.finding_id,
        question=payload.question,
        rationale=payload.rationale,
        impact=payload.impact,
        proposed_wording=payload.proposed_wording,
        owner=payload.owner,
        created_by=actor_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(clarification)
    session.flush()
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "clarification.created",
        "clarification",
        clarification.id,
    )
    session.commit()
    return clarification_data(clarification)


@app.get("/projects/{project_id}/clarifications", response_model=None, tags=["clarifications"])
def list_clarifications(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    return [
        clarification_data(clarification)
        for clarification in session.scalars(
            select(Clarification)
            .where(Clarification.project_id == project_id, Clarification.tenant_id == tenant_id)
            .order_by(Clarification.created_at.desc())
        )
    ]


@app.get("/projects/{project_id}/baselines", response_model=None, tags=["baselines"])
def list_baselines(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    return [
        baseline_data(baseline)
        for baseline in session.scalars(
            select(Baseline)
            .where(Baseline.project_id == project_id, Baseline.tenant_id == tenant_id)
            .order_by(Baseline.version.desc())
        )
    ]


@app.post("/projects/{project_id}/formula-lab/evaluate", tags=["formula-lab"])
def evaluate_formula_lab(
    project_id: UUID,
    payload: FormulaEvaluationInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, _ = context
    if (
        session.scalar(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        is None
    ):
        raise HTTPException(404, "project not found")
    try:
        result = evaluate_formula(payload.template, payload.inputs)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    output_value = str(result.value)
    reproducibility_hash = hashlib.sha256(
        json.dumps(
            {"template": payload.template, "inputs": payload.inputs, "output": output_value},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    session.add(
        FormulaCalculation(
            tenant_id=tenant_id,
            project_id=project_id,
            template=payload.template,
            inputs=payload.inputs,
            output_value=output_value,
            reproducibility_hash=reproducibility_hash,
            created_at=datetime.now(UTC),
        )
    )
    session.commit()
    return {
        "template": result.template,
        "formula_version": "1.0",
        "formula": result.formula,
        "output_value": output_value,
        "unit": result.unit,
        "official_evaluation": False,
        "reproducibility_hash": reproducibility_hash,
    }


@app.post(
    "/projects/{project_id}/formula-lab/configurations",
    status_code=201,
    response_model=None,
    tags=["formula-lab"],
)
def create_formula_config(
    project_id: UUID,
    payload: FormulaConfigInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    if (
        session.scalar(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        is None
    ):
        raise HTTPException(404, "project not found")
    latest_config = session.scalar(
        select(FormulaConfig)
        .where(FormulaConfig.project_id == project_id, FormulaConfig.tenant_id == tenant_id)
        .order_by(FormulaConfig.version.desc())
    )
    config = FormulaConfig(
        tenant_id=tenant_id,
        project_id=project_id,
        template=payload.template,
        version=(latest_config.version if latest_config else 0) + 1,
        source_clause_text=payload.source_clause_text,
        approved=False,
        created_by=actor_id,
        created_at=datetime.now(UTC),
    )
    session.add(config)
    session.flush()
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "formula_config.created",
        "formula_config",
        config.id,
    )
    session.commit()
    return formula_config_data(config, [])


@app.get(
    "/projects/{project_id}/formula-lab/configurations", response_model=None, tags=["formula-lab"]
)
def list_formula_configs(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    configs = list(
        session.scalars(
            select(FormulaConfig)
            .where(FormulaConfig.project_id == project_id, FormulaConfig.tenant_id == tenant_id)
            .order_by(FormulaConfig.version.desc())
        )
    )
    if (
        not configs
        and session.scalar(
            select(Project).where(Project.id == project_id, Project.tenant_id == tenant_id)
        )
        is None
    ):
        raise HTTPException(404, "project not found")
    calculations = list(
        session.scalars(
            select(FormulaCalculation)
            .where(
                FormulaCalculation.project_id == project_id,
                FormulaCalculation.tenant_id == tenant_id,
                FormulaCalculation.formula_config_id.is_not(None),
            )
            .order_by(FormulaCalculation.created_at.desc())
        )
    )
    return [
        formula_config_data(
            config, [item for item in calculations if item.formula_config_id == config.id]
        )
        for config in configs
    ]


@app.post(
    "/projects/{project_id}/formula-lab/configurations/{config_id}/evaluate",
    response_model=None,
    tags=["formula-lab"],
)
def evaluate_formula_config(
    project_id: UUID,
    config_id: UUID,
    payload: FormulaConfigEvaluationInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, _ = context
    config = session.scalar(
        select(FormulaConfig).where(
            FormulaConfig.id == config_id,
            FormulaConfig.project_id == project_id,
            FormulaConfig.tenant_id == tenant_id,
        )
    )
    if config is None:
        raise HTTPException(404, "formula configuration not found")
    try:
        result = evaluate_formula(FormulaTemplate(config.template), payload.inputs)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    output_value = str(result.value)
    reproducibility_hash = hashlib.sha256(
        json.dumps(
            {
                "config_id": str(config.id),
                "config_version": config.version,
                "template": config.template,
                "inputs": payload.inputs,
                "output": output_value,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    calculation = FormulaCalculation(
        tenant_id=tenant_id,
        project_id=project_id,
        formula_config_id=config.id,
        template=config.template,
        inputs=payload.inputs,
        output_value=output_value,
        reproducibility_hash=reproducibility_hash,
        created_at=datetime.now(UTC),
    )
    session.add(calculation)
    session.commit()
    return {
        **formula_calculation_data(calculation),
        "formula_version": "1.0",
        "formula": result.formula,
        "unit": result.unit,
        "official_evaluation": False,
    }


@app.post(
    "/projects/{project_id}/baselines/freeze",
    status_code=201,
    response_model=None,
    tags=["baselines"],
)
def freeze_baseline(
    project_id: UUID,
    payload: BaselineFreezeInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    membership = session.scalar(
        select(Membership).where(Membership.tenant_id == tenant_id, Membership.user_id == actor_id)
    )
    if membership is None or membership.role not in {"owner", "organization_owner", "approver"}:
        raise HTTPException(403, "an approver role is required to freeze a baseline")
    basis = session.scalar(
        select(DesignBasisVersion)
        .where(
            DesignBasisVersion.project_id == project_id,
            DesignBasisVersion.tenant_id == tenant_id,
            DesignBasisVersion.status == "approved",
        )
        .order_by(DesignBasisVersion.version.desc())
    )
    if basis is None:
        raise HTTPException(409, "an approved Design Basis is required")
    documents = list(
        session.scalars(
            select(Document).where(
                Document.project_id == project_id, Document.tenant_id == tenant_id
            )
        )
    )
    requirements = list(
        session.scalars(
            select(Requirement).where(
                Requirement.project_id == project_id, Requirement.tenant_id == tenant_id
            )
        )
    )
    if not documents or not any(item.state == RequirementState.VERIFIED for item in requirements):
        raise HTTPException(409, "a baseline requires source documents and verified requirements")
    if any(
        item.state in {RequirementState.PROPOSED, RequirementState.CLARIFICATION_REQUIRED}
        for item in requirements
    ):
        raise HTTPException(409, "all requirements must be resolved before baseline freeze")
    blocking_findings = list(
        session.scalars(
            select(Finding).where(
                Finding.project_id == project_id,
                Finding.tenant_id == tenant_id,
                Finding.state == FindingState.OPEN,
                Finding.severity.in_(["critical", "high"]),
            )
        )
    )
    if blocking_findings:
        raise HTTPException(
            409, "high or critical findings must be resolved before baseline freeze"
        )
    previous = session.scalar(
        select(Baseline)
        .where(Baseline.project_id == project_id, Baseline.tenant_id == tenant_id)
        .order_by(Baseline.version.desc())
    )
    data: dict[str, object] = {
        "design_basis": {"id": str(basis.id), "version": basis.version},
        "documents": [{"id": str(item.id), "sha256": item.sha256} for item in documents],
        "requirements": [
            {"id": str(item.id), "key": item.stable_key, "version": item.version}
            for item in requirements
            if item.state == RequirementState.VERIFIED
        ],
        "rule_catalogue": [{"id": rule.rule_id, "version": rule.version} for rule in RULES],
    }
    content_hash = hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    baseline = Baseline(
        tenant_id=tenant_id,
        project_id=project_id,
        version=(previous.version + 1) if previous else 1,
        content_hash=content_hash,
        data=data,
        frozen_by=actor_id,
        frozen_at=datetime.now(UTC),
    )
    session.add(baseline)
    session.flush()
    session.add(
        ApprovalRecord(
            tenant_id=tenant_id,
            project_id=project_id,
            object_type="baseline",
            object_id=baseline.id,
            object_version=baseline.version,
            decision="frozen",
            role=membership.role,
            actor_id=actor_id,
            reason=payload.reason,
            previous_state="draft",
            new_state="frozen",
            created_at=datetime.now(UTC),
        )
    )
    audit(session, tenant_id, project_id, actor_id, "baseline.frozen", "baseline", baseline.id)
    session.commit()
    return baseline_data(baseline)


@app.post(
    "/projects/{project_id}/requirements/{requirement_id}/review",
    response_model=None,
    tags=["requirements"],
)
def review_requirement(
    project_id: UUID,
    requirement_id: UUID,
    payload: ReviewInput,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    tenant_id, actor_id = context
    requirement = session.scalar(
        select(Requirement).where(
            Requirement.id == requirement_id,
            Requirement.project_id == project_id,
            Requirement.tenant_id == tenant_id,
        )
    )
    if requirement is None:
        raise HTTPException(404, "requirement not found")
    if requirement.version != payload.expected_version:
        raise HTTPException(409, "stale requirement version")
    if not can_transition(RequirementState(requirement.state), payload.decision):
        raise HTTPException(409, "invalid requirement state transition")
    if payload.decision == RequirementState.VERIFIED:
        evidence = tuple(
            EvidenceReference(evidence_span_id=span.id, exact_text=span.exact_text)
            for span in session.scalars(
                select(EvidenceSpan)
                .join(RequirementEvidence, EvidenceSpan.id == RequirementEvidence.evidence_span_id)
                .where(
                    RequirementEvidence.requirement_id == requirement.id,
                    RequirementEvidence.verified.is_(True),
                )
            )
        )
        try:
            require_verifiable_evidence(payload.decision, evidence)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
    requirement.state = payload.decision
    requirement.version += 1
    session.add(
        ReviewDecision(
            requirement_id=requirement.id,
            actor_id=actor_id,
            decision=payload.decision,
            created_at=datetime.now(UTC),
        )
    )
    audit(
        session,
        tenant_id,
        project_id,
        actor_id,
        "requirement.reviewed",
        "requirement",
        requirement.id,
    )
    session.commit()
    return requirement_data(requirement)


@app.get("/projects/{project_id}/audit", response_model=None, tags=["audit"])
def list_audit_events(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> list[dict[str, object]]:
    tenant_id, _ = context
    events = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.project_id == project_id, AuditEvent.tenant_id == tenant_id)
        .order_by(AuditEvent.created_at, AuditEvent.id)
    )
    return [
        {
            "id": event.id,
            "actor_id": event.actor_id,
            "action": event.action,
            "object_type": event.object_type,
            "object_id": event.object_id,
            "created_at": event.created_at,
        }
        for event in events
    ]


@app.get("/projects/{project_id}/requirements/export.csv", tags=["requirements"])
def export_requirements(
    project_id: UUID,
    context: tuple[UUID, UUID] = Depends(actor_context),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    tenant_id, _ = context
    rows = session.scalars(
        select(Requirement)
        .where(
            Requirement.project_id == project_id,
            Requirement.tenant_id == tenant_id,
            Requirement.state == RequirementState.VERIFIED,
        )
        .order_by(Requirement.stable_key)
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["stable_key", "taxonomy", "status", "requirement"])
    for row in rows:
        writer.writerow([row.stable_key, row.taxonomy, row.state, row.text])
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=requirements.csv"},
    )
