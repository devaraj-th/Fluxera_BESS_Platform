from io import BytesIO
from uuid import uuid4

from apps.api import db
from apps.api.main import app
from apps.api.settings import get_settings
from fastapi.testclient import TestClient
from pypdf import PdfWriter


def pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_manual_evidence_review_export_and_tenant_isolation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'workflow.db'}")
    monkeypatch.setenv("FLUXERA_STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)
    actor_id = str(uuid4())
    tenant = client.post("/tenants?name=Tenant A", headers={"X-Actor-Id": actor_id})
    tenant_id = tenant.json()["id"]
    headers = {"X-Tenant-Id": tenant_id, "X-Actor-Id": actor_id}
    project = client.post("/projects", headers=headers, json={"name": "CEB"})
    project_id = project.json()["id"]

    upload = client.post(
        f"/projects/{project_id}/documents",
        headers=headers,
        files={"file": ("source.pdf", pdf_bytes(), "application/pdf")},
        data={
            "document_type": "rfp",
            "volume": "I",
            "title": "Request for Selection",
            "revision": "0",
            "issue_date": "2026-08-15",
            "tender_number": "CEB-001",
        },
    )
    assert upload.status_code == 201
    assert upload.json()["document_type"] == "rfp"
    assert upload.json()["page_count"] == 1
    duplicate = client.post(
        f"/projects/{project_id}/documents",
        headers=headers,
        files={"file": ("source.pdf", pdf_bytes(), "application/pdf")},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == upload.json()["id"]
    report = client.get(f"/projects/{project_id}/pre-bid-report", headers=headers)
    assert report.status_code == 200
    assert report.json()["document_count"] == 1
    assert report.json()["pages_extracted"] == 1
    assert report.json()["requirements_created"] == 0
    assert report.json()["report_status"] == "review_ready"

    page_id = client.get(f"/projects/{project_id}/pages", headers=headers).json()[0]["id"]
    evidence = client.post(
        f"/projects/{project_id}/evidence",
        headers=headers,
        json={"page_id": page_id, "exact_text": "Selected source context"},
    )
    assert evidence.status_code == 201
    assert evidence.json()["extraction_method"] == "human_transcription"
    span_id = evidence.json()["id"]
    requirement = client.post(
        f"/projects/{project_id}/requirements",
        headers=headers,
        json={
            "stable_key": "CEB160-PER-0042",
            "taxonomy": "PER",
            "text": "Supplier shall provide source context.",
            "evidence_span_ids": [span_id],
            "title": "Round-trip efficiency",
            "metric": "round-trip efficiency",
            "comparator": ">=",
            "minimum_value": 85,
            "unit": "%",
            "measurement_boundary": "AC-AC at delivery point",
            "mandatory": True,
            "evaluation_treatment": "pass_fail",
            "owner_discipline": "engineering",
        },
    )
    requirement_id = requirement.json()["id"]
    assert requirement.json()["minimum_value"] == 85
    assert requirement.json()["measurement_boundary"] == "AC-AC at delivery point"
    addendum = client.post(
        f"/projects/{project_id}/documents",
        headers=headers,
        files={"file": ("addendum.pdf", pdf_bytes() + b"addendum", "application/pdf")},
        data={"document_type": "addendum", "addendum_number": "1"},
    )
    assert addendum.status_code == 201
    relationship = client.post(
        f"/projects/{project_id}/document-relationships",
        headers=headers,
        json={
            "source_document_id": addendum.json()["id"],
            "target_document_id": upload.json()["id"],
            "relationship_type": "amends",
            "affected_clauses": ["4.2"],
            "reason": "Addendum updates the capacity requirement.",
        },
    )
    assert relationship.status_code == 201
    impact = client.get(
        f"/projects/{project_id}/document-relationships/{relationship.json()['id']}/impact",
        headers=headers,
    )
    assert impact.status_code == 200
    assert impact.json()["requires_re_review"] is True
    assert [item["id"] for item in impact.json()["impacted_requirements"]] == [requirement_id]
    detailed = client.get(f"/projects/{project_id}/requirements/detailed", headers=headers)
    assert detailed.status_code == 200
    assert detailed.json()[0]["evidence"][0]["page_number"] == 1
    assert detailed.json()[0]["evidence"][0]["verified"] is False
    review_url = f"/projects/{project_id}/requirements/{requirement_id}/review"
    blocked = client.post(
        review_url, headers=headers, json={"decision": "verified", "expected_version": 1}
    )
    assert blocked.status_code == 422

    verified_evidence = client.post(
        f"/projects/{project_id}/requirements/{requirement_id}/evidence/{span_id}/verify",
        headers=headers,
    )
    assert verified_evidence.status_code == 200
    verified = client.post(
        review_url, headers=headers, json={"decision": "verified", "expected_version": 1}
    )
    assert verified.status_code == 200
    assert verified.json()["state"] == "verified"
    report = client.get(f"/projects/{project_id}/pre-bid-report", headers=headers)
    assert report.json()["requirements_by_state"]["verified"] == 1
    assert report.json()["verified_evidence_count"] == 1
    assert report.json()["ready_for_export"] is True
    export = client.get(f"/projects/{project_id}/requirements/export.csv", headers=headers)
    assert export.status_code == 200
    assert "CEB160-PER-0042" in export.text
    audit = client.get(f"/projects/{project_id}/audit", headers=headers)
    assert audit.status_code == 200
    assert any(event["action"] == "requirement.reviewed" for event in audit.json())

    other_headers = {"X-Tenant-Id": str(uuid4()), "X-Actor-Id": str(uuid4())}
    assert client.get(f"/projects/{project_id}/audit", headers=other_headers).status_code == 403
    assert (
        client.get(f"/projects/{project_id}/requirements", headers=other_headers).status_code == 403
    )
