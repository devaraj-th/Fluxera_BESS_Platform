from uuid import uuid4

from apps.api import db
from apps.api.main import app
from apps.api.settings import get_settings
from fastapi.testclient import TestClient


def test_bidder_profile_requires_bid_intelligence_project(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'bid.db'}")
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)
    actor_id = str(uuid4())
    tenant = client.post("/tenants?name=Bidder", headers={"X-Actor-Id": actor_id}).json()
    headers = {"X-Actor-Id": actor_id, "X-Tenant-Id": tenant["id"]}
    pre_bid = client.post("/projects", headers=headers, json={"name": "Pre-Bid"}).json()
    assert (
        client.post(
            f"/projects/{pre_bid['id']}/bidder-profile",
            headers=headers,
            json={"legal_entity": "Fluxera Integrator Pvt Ltd"},
        ).status_code
        == 409
    )
    bid_project = client.post(
        "/projects",
        headers=headers,
        json={"name": "Bid", "module_mode": "bid_intelligence"},
    ).json()
    profile = client.post(
        f"/projects/{bid_project['id']}/bidder-profile",
        headers=headers,
        json={"legal_entity": "Fluxera Integrator Pvt Ltd", "parent_entity": "Fluxera Group"},
    )
    assert profile.status_code == 201
    assert profile.json()["legal_entity"] == "Fluxera Integrator Pvt Ltd"
