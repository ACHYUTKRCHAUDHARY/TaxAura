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


def test_frontend_is_served_with_security_headers() -> None:
    with TestClient(app) as client:
        response = client.get("/app/")
    assert response.status_code == 200
    assert "Tax clarity" in response.text
    assert "default-src 'self'" in response.headers["content-security-policy"]
