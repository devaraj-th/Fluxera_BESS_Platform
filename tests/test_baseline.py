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


def test_baseline_freeze_requires_resolved_findings_and_is_immutable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'baseline.db'}")
    monkeypatch.setenv("FLUXERA_STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)
    actor_id = str(uuid4())
    tenant = client.post("/tenants?name=Baseline", headers={"X-Actor-Id": actor_id}).json()
    headers = {"X-Actor-Id": actor_id, "X-Tenant-Id": tenant["id"]}
    project_id = client.post("/projects", headers=headers, json={"name": "BESS"}).json()["id"]
    basis = client.post(
        f"/projects/{project_id}/design-basis",
        headers=headers,
        json={
            "rated_power_mw": 100,
            "nominal_energy_mwh": 200,
            "required_usable_energy_mwh": 190,
            "duration_hours": 2,
            "project_life_years": 15,
            "availability_target_percent": 95,
            "round_trip_efficiency_target_percent": 85,
            "cycles_per_day": 1,
            "use_case": "capacity",
            "ac_dc_boundary": "AC-AC at delivery point",
        },
    ).json()
    client.post(f"/projects/{project_id}/design-basis/{basis['id']}/approve", headers=headers)
    document = client.post(
        f"/projects/{project_id}/documents",
        headers=headers,
        files={"file": ("source.pdf", pdf_bytes(), "application/pdf")},
    ).json()
    page_id = client.get(f"/projects/{project_id}/pages", headers=headers).json()[0]["id"]
    evidence_id = client.post(
        f"/projects/{project_id}/evidence",
        headers=headers,
        json={"page_id": page_id, "exact_text": "Selected source context"},
    ).json()["id"]
    requirement = client.post(
        f"/projects/{project_id}/requirements",
        headers=headers,
        json={
            "stable_key": "BES100-ADM-0001",
            "taxonomy": "ADM",
            "text": "Supplier shall provide an administrative declaration.",
            "evidence_span_ids": [evidence_id],
        },
    ).json()
    client.post(
        f"/projects/{project_id}/requirements/{requirement['id']}/evidence/{evidence_id}/verify",
        headers=headers,
    )
    client.post(
        f"/projects/{project_id}/requirements/{requirement['id']}/review",
        headers=headers,
        json={"decision": "verified", "expected_version": 1},
    )
    finding = client.post(f"/projects/{project_id}/findings/run", headers=headers).json()[0]
    assert (
        client.post(
            f"/projects/{project_id}/baselines/freeze", headers=headers, json={"reason": "Ready"}
        ).status_code
        == 409
    )
    clarification = client.post(
        f"/projects/{project_id}/clarifications",
        headers=headers,
        json={
            "finding_id": finding["id"],
            "question": "Confirm schedule.",
            "rationale": "Baseline",
        },
    )
    assert clarification.status_code == 201
    client.post(
        f"/projects/{project_id}/findings/{finding['id']}/resolve",
        headers=headers,
        json={"state": "accepted_risk", "reason": "Approved exception."},
    )
    baseline = client.post(
        f"/projects/{project_id}/baselines/freeze",
        headers=headers,
        json={"reason": "Approved for issue."},
    )
    assert baseline.status_code == 201
    assert len(baseline.json()["content_hash"]) == 64
    assert (
        client.get(f"/projects/{project_id}/baselines", headers=headers).json()[0]["id"]
        == baseline.json()["id"]
    )
    assert document["sha256"] in [item["sha256"] for item in baseline.json()["data"]["documents"]]
