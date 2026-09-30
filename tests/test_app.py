from fastapi.testclient import TestClient

from aura.main import app


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]


def test_tax_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/tax/compare",
            json={"annual_salary": 1_000_000, "old_regime_deductions": 0},
        )
    assert response.status_code == 401


def test_api_does_not_expose_frontend_source() -> None:
    with TestClient(app) as client:
        for path in ("/app/", "/app/package.json", "/app/.env.local"):
            assert client.get(path).status_code == 404
