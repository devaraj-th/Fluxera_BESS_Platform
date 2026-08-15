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
    )
    assert upload.status_code == 201
    duplicate = client.post(
        f"/projects/{project_id}/documents",
        headers=headers,
        files={"file": ("source.pdf", pdf_bytes(), "application/pdf")},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == upload.json()["id"]

    page_id = client.get(f"/projects/{project_id}/pages", headers=headers).json()[0]["id"]
    evidence = client.post(
        f"/projects/{project_id}/evidence",
        headers=headers,
        json={"page_id": page_id, "exact_text": "Selected source context"},
    )
    assert evidence.status_code == 201
    span_id = evidence.json()["id"]
    requirement = client.post(
        f"/projects/{project_id}/requirements",
        headers=headers,
        json={
            "stable_key": "CEB160-PER-0042",
            "taxonomy": "PER",
            "text": "Supplier shall provide source context.",
            "evidence_span_ids": [span_id],
        },
    )
    requirement_id = requirement.json()["id"]
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
