from apps.api.main import app
from fastapi.testclient import TestClient


def test_health_is_available() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_configuration_without_leaking_secrets() -> None:
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
