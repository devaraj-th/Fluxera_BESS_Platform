from uuid import uuid4

from apps.api import db
from apps.api.main import app
from apps.api.settings import get_settings
from fastapi.testclient import TestClient


def design_basis_payload() -> dict[str, object]:
    return {
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
    }


def test_persisted_findings_are_idempotent_and_require_a_reason(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'findings.db'}")
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)
    actor_id = str(uuid4())
    tenant = client.post("/tenants?name=Findings", headers={"X-Actor-Id": actor_id}).json()
    headers = {"X-Actor-Id": actor_id, "X-Tenant-Id": tenant["id"]}
    project = client.post("/projects", headers=headers, json={"name": "BESS"}).json()
    project_id = project["id"]
    basis = client.post(
        f"/projects/{project_id}/design-basis", headers=headers, json=design_basis_payload()
    ).json()
    assert (
        client.post(
            f"/projects/{project_id}/design-basis/{basis['id']}/approve", headers=headers
        ).status_code
        == 200
    )

    first_run = client.post(f"/projects/{project_id}/findings/run", headers=headers)
    assert first_run.status_code == 200
    assert len(first_run.json()) == 1
    finding_id = first_run.json()[0]["id"]
    assert (
        client.post(f"/projects/{project_id}/findings/run", headers=headers).json()
        == first_run.json()
    )
    assert (
        client.post(
            f"/projects/{project_id}/findings/{finding_id}/resolve",
            headers=headers,
            json={"state": "accepted_risk", "reason": "Tender issue approved by engineering."},
        ).json()["state"]
        == "accepted_risk"
    )
    assert client.get(f"/projects/{project_id}/findings", headers=headers).json()[0]["resolution"]
