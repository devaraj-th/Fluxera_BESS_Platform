import csv
import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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

from apps.api.db import Base, get_engine, get_session
from apps.api.models import (
    AuditEvent,
    Document,
    DocumentState,
    EvidenceSpan,
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


class EvidenceInput(BaseModel):
    page_id: UUID
    exact_text: str = Field(min_length=1)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)


class RequirementInput(BaseModel):
    stable_key: str
    taxonomy: TaxonomyCode
    text: str = Field(min_length=1)
    evidence_span_ids: list[UUID] = Field(min_length=1)


class ReviewInput(BaseModel):
    decision: RequirementState
    expected_version: int = Field(ge=1)


def actor_context(
    x_tenant_id: UUID | None = Header(default=None),
    x_actor_id: UUID | None = Header(default=None),
    session: Session = Depends(get_session),
) -> tuple[UUID, UUID]:
    if x_tenant_id is None or x_actor_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="tenant and actor context required"
        )
    if (
        session.scalar(
            select(Membership).where(
                Membership.tenant_id == x_tenant_id, Membership.user_id == x_actor_id
            )
        )
        is None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="tenant membership required"
        )
    return x_tenant_id, x_actor_id


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
    }


def document_data(document: Document) -> dict[str, object]:
    return {
        "id": document.id,
        "project_id": document.project_id,
        "filename": document.filename,
        "sha256": document.sha256,
        "state": document.state,
        "byte_size": document.byte_size,
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
    }


def requirement_data(requirement: Requirement) -> dict[str, object]:
    return {
        "id": requirement.id,
        "project_id": requirement.project_id,
        "stable_key": requirement.stable_key,
        "taxonomy": requirement.taxonomy,
        "text": requirement.text,
        "state": requirement.state,
        "version": requirement.version,
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, str]:
    return {"status": "ready"}


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
    project = Project(tenant_id=tenant_id, name=payload.name, timezone=payload.timezone)
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


@app.post(
    "/projects/{project_id}/documents", status_code=201, response_model=None, tags=["documents"]
)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
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
        filename=file.filename or "upload.pdf",
        sha256=digest,
        object_key=object_key,
        mime_type="application/pdf",
        byte_size=len(content),
        state=DocumentState.REVIEW_READY,
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
