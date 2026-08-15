from uuid import uuid4

from apps.api import db
from apps.api.main import app
from apps.api.settings import get_settings
from fastapi.testclient import TestClient


def payload(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "rated_power_mw": 100,
        "nominal_energy_mwh": 400,
        "required_usable_energy_mwh": 380,
        "duration_hours": 4,
        "project_life_years": 20,
        "availability_target_percent": 98,
        "round_trip_efficiency_target_percent": 88,
        "cycles_per_day": 1,
        "use_case": "capacity",
        "ac_dc_boundary": "AC point of interconnection",
    }
    value.update(overrides)
    return value


def test_design_basis_versions_and_approval(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'basis.db'}")
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)
    actor_id = str(uuid4())
    tenant = client.post("/tenants?name=Basis", headers={"X-Actor-Id": actor_id}).json()
    headers = {"X-Actor-Id": actor_id, "X-Tenant-Id": tenant["id"]}
    project = client.post("/projects", headers=headers, json={"name": "BESS"}).json()
    project_id = project["id"]

    invalid = client.post(
        f"/projects/{project_id}/design-basis", headers=headers, json=payload(duration_hours=3)
    )
    assert invalid.status_code == 422
    first = client.post(f"/projects/{project_id}/design-basis", headers=headers, json=payload())
    assert first.status_code == 201
    assert first.json()["version"] == 1
    approved = client.post(
        f"/projects/{project_id}/design-basis/{first.json()['id']}/approve", headers=headers
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    second = client.post(
        f"/projects/{project_id}/design-basis", headers=headers, json=payload(cycles_per_day=2)
    )
    assert second.json()["version"] == 2
    assert (
        client.get(f"/projects/{project_id}/design-basis", headers=headers).json()["version"] == 2
    )
