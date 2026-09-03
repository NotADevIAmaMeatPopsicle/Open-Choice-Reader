from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.auth_session"))
    reload(import_module("app.models.collection"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.theme_profile"))
    reload(import_module("app.models.user"))
    reload(import_module("app.models.user_invite"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.auth"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.playback"))
    reload(import_module("app.services.settings"))
    reload(import_module("app.services.themes"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.auth"))
    reload(import_module("app.api.playback"))
    reload(import_module("app.api.settings"))
    reload(import_module("app.api.themes"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'auth-api.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_bootstrap_admin_creates_first_admin_and_starts_session(client: TestClient) -> None:
    response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["username"] == "admin"
    assert payload["user"]["role"] == "admin"

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "admin"


def test_bootstrap_admin_rejects_public_host_behind_loopback_proxy(client: TestClient) -> None:
    response = client.post(
        "https://reader.example.test/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 403


def test_bootstrap_admin_rejects_forwarded_request_even_with_local_host(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/auth/bootstrap-admin",
        headers={"X-Forwarded-For": "198.51.100.25"},
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 403


def test_bootstrap_admin_accepts_remote_host_with_configured_token(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "auth_bootstrap_token", "one-time-bootstrap-token")

    response = client.post(
        "https://reader.example.test/api/auth/bootstrap-admin",
        headers={"X-Bootstrap-Token": "one-time-bootstrap-token"},
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )

    assert response.status_code == 201


def test_bootstrap_admin_is_blocked_after_first_user_exists(client: TestClient) -> None:
    first_response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )
    assert first_response.status_code == 201

    second_response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "OtherAdmin",
            "display_name": "Other Admin",
            "password": "correct horse battery staple",
        },
    )

    assert second_response.status_code == 409


def test_login_logout_and_change_password_round_trip(client: TestClient) -> None:
    bootstrap_response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )
    assert bootstrap_response.status_code == 201

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204
    assert client.get("/api/auth/me").status_code == 401

    invalid_login = client.post(
        "/api/auth/login",
        json={"username": "Admin", "password": "wrong password"},
    )
    assert invalid_login.status_code == 401

    login_response = client.post(
        "/api/auth/login",
        json={"username": "Admin", "password": "correct horse battery staple"},
    )
    assert login_response.status_code == 200
    assert client.get("/api/auth/me").status_code == 200

    change_response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "correct horse battery staple",
            "new_password": "new correct horse battery staple",
        },
    )
    assert change_response.status_code == 200

    logout_again = client.post("/api/auth/logout")
    assert logout_again.status_code == 204

    old_login = client.post(
        "/api/auth/login",
        json={"username": "Admin", "password": "correct horse battery staple"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"username": "Admin", "password": "new correct horse battery staple"},
    )
    assert new_login.status_code == 200


def test_bootstrap_status_reports_first_run_state(client: TestClient) -> None:
    initial_response = client.get("/api/auth/bootstrap-status")
    assert initial_response.status_code == 200
    assert initial_response.json() == {"bootstrap_available": True}

    bootstrap_response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )
    assert bootstrap_response.status_code == 201

    final_response = client.get("/api/auth/bootstrap-status")
    assert final_response.status_code == 200
    assert final_response.json() == {"bootstrap_available": False}


def test_admin_can_list_users_and_manage_invites(client: TestClient) -> None:
    bootstrap_response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )
    assert bootstrap_response.status_code == 201

    users_response = client.get("/api/auth/users")
    assert users_response.status_code == 200
    users_payload = users_response.json()
    assert [user["username"] for user in users_payload] == ["admin"]

    create_invite_response = client.post(
        "/api/auth/invites",
        json={
            "display_name_hint": "Casey Reader",
            "role_to_grant": "member",
            "expires_in_days": 7,
        },
    )
    assert create_invite_response.status_code == 201
    invite_payload = create_invite_response.json()
    assert invite_payload["token"]
    assert invite_payload["invite"]["display_name_hint"] == "Casey Reader"
    assert invite_payload["invite"]["role_to_grant"] == "member"
    assert invite_payload["invite"]["revoked_at"] is None

    list_invites_response = client.get("/api/auth/invites")
    assert list_invites_response.status_code == 200
    invite_list = list_invites_response.json()
    assert len(invite_list) == 1
    assert invite_list[0]["id"] == invite_payload["invite"]["id"]

    revoke_response = client.post(f"/api/auth/invites/{invite_payload['invite']['id']}/revoke")
    assert revoke_response.status_code == 200
    assert revoke_response.json()["revoked_at"] is not None


def test_claim_invite_round_trip_succeeds_when_invite_has_expiry(client: TestClient) -> None:
    bootstrap_response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )
    assert bootstrap_response.status_code == 201

    create_invite_response = client.post(
        "/api/auth/invites",
        json={
            "display_name_hint": "Casey Reader",
            "role_to_grant": "member",
            "expires_in_days": 7,
        },
    )
    assert create_invite_response.status_code == 201
    invite_payload = create_invite_response.json()

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    claim_response = client.post(
        "/api/auth/claim-invite",
        json={
            "token": invite_payload["token"],
            "username": "casey",
            "display_name": "Casey Reader",
            "password": "reader-password-123",
        },
    )

    assert claim_response.status_code == 201
    assert claim_response.json()["user"]["username"] == "casey"


def test_member_cannot_access_admin_user_or_invite_routes(client: TestClient) -> None:
    bootstrap_response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "Admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )
    assert bootstrap_response.status_code == 201

    auth_service = import_module("app.services.auth")
    db_module = import_module("app.db")
    with db_module.session_scope() as session:
        auth_service.create_user(
            session,
            username="member",
            display_name="Member User",
            password="member password 123",
            role="member",
        )

    logout_response = client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    login_response = client.post(
        "/api/auth/login",
        json={"username": "member", "password": "member password 123"},
    )
    assert login_response.status_code == 200

    for path, method in (
        ("/api/auth/users", "GET"),
        ("/api/auth/invites", "GET"),
        ("/api/auth/invites", "POST"),
    ):
        if method == "GET":
            response = client.get(path)
        else:
            response = client.post(path, json={"display_name_hint": "Blocked", "role_to_grant": "member"})
        assert response.status_code == 403
