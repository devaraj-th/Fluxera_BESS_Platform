from apps.api import db
from apps.api.main import app
from apps.api.settings import get_settings
from fastapi.testclient import TestClient


def test_bootstrap_login_and_logout_revoke_session(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLUXERA_DATABASE_URL", f"sqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setenv("FLUXERA_ENVIRONMENT", "local")
    get_settings.cache_clear()
    db._engine = None
    client = TestClient(app)

    bootstrap = client.post(
        "/auth/bootstrap",
        json={
            "organization_name": "Fluxera Test",
            "display_name": "Owner",
            "email": "owner@example.test",
            "password": "a-long-local-password",
        },
    )
    assert bootstrap.status_code == 201
    payload = bootstrap.json()
    headers = {
        "Authorization": f"Bearer {payload['access_token']}",
        "X-Tenant-Id": payload["organization"]["id"],
    }
    assert client.get("/projects", headers=headers).status_code == 200
    assert (
        client.get(
            "/projects",
            headers={
                "Authorization": "Bearer forged",
                "X-Tenant-Id": payload["organization"]["id"],
            },
        ).status_code
        == 401
    )

    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/projects", headers=headers).status_code == 401

    login = client.post(
        "/auth/login",
        json={"email": "owner@example.test", "password": "a-long-local-password"},
    )
    assert login.status_code == 200
