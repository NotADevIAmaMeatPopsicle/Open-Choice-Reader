from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


def test_local_development_origin_is_allowed_for_api_requests() -> None:
    client = TestClient(app)

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_unknown_web_origin_is_not_reflected() -> None:
    client = TestClient(app)

    response = client.options(
        "/api/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_chrome_extension_origin_requires_explicit_configuration() -> None:
    client = TestClient(app)

    response = client.options(
        "/api/auth/me",
        headers={
            "Origin": "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_unknown_origin_cannot_send_state_changing_request() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        headers={"Origin": "https://example.test"},
        json={"username": "admin", "password": "not-the-password"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Request origin is not allowed"}


def test_declared_oversized_request_is_rejected_before_parsing() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/auth/login",
        headers={"Content-Length": str(settings.request_body_max_bytes + 1)},
        content=b"{}",
    )

    assert response.status_code == 413
