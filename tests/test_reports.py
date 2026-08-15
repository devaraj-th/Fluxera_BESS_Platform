from uuid import uuid4

from apps.api import db
from apps.api.main import app
from apps.api.settings import get_settings
from fastapi.testclient import TestClient


def test_assurance_report_is_project_scoped(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'reports.db'}")
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)
    actor_id = str(uuid4())
    tenant = client.post("/tenants?name=Reports", headers={"X-Actor-Id": actor_id}).json()
    headers = {"X-Actor-Id": actor_id, "X-Tenant-Id": tenant["id"]}
    project = client.post("/projects", headers=headers, json={"name": "Assurance"}).json()
    report = client.get(f"/projects/{project['id']}/pre-bid-assurance-report", headers=headers)
    assert report.status_code == 200
    assert report.json()["report_type"] == "pre_bid_assurance"
    assert report.json()["project"]["id"] == project["id"]
    assert "procurement decision" in report.json()["limitations"][0]
