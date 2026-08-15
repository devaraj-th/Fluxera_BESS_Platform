from uuid import uuid4

from apps.api import db
from apps.api.main import app
from apps.api.settings import get_settings
from fastapi.testclient import TestClient


def test_formula_config_evaluation_retains_project_scoped_history(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'formula-lab.db'}")
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)
    actor_id = str(uuid4())
    tenant = client.post("/tenants?name=Formula", headers={"X-Actor-Id": actor_id}).json()
    headers = {"X-Actor-Id": actor_id, "X-Tenant-Id": tenant["id"]}
    project_id = client.post("/projects", headers=headers, json={"name": "BESS"}).json()["id"]

    config = client.post(
        f"/projects/{project_id}/formula-lab/configurations",
        headers=headers,
        json={
            "template": "rte_adjusted_capacity_charge",
            "source_clause_text": "Adjusted for guaranteed RTE.",
        },
    )
    assert config.status_code == 201
    assert config.json()["version"] == 1
    assert config.json()["approved"] is False

    evaluation = client.post(
        f"/projects/{project_id}/formula-lab/configurations/{config.json()['id']}/evaluate",
        headers=headers,
        json={
            "inputs": {
                "quoted_capacity_charge": 100_000,
                "baseline_rte_percent": 85,
                "guaranteed_rte_percent": 80,
            }
        },
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["output_value"] == "105000.000"

    configs = client.get(f"/projects/{project_id}/formula-lab/configurations", headers=headers)
    assert configs.status_code == 200
    assert configs.json()[0]["source_clause_text"] == "Adjusted for guaranteed RTE."
    assert configs.json()[0]["calculations"][0]["id"] == evaluation.json()["id"]
