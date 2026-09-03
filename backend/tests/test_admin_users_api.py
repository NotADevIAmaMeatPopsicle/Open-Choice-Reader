from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    for module_name in (
        "app.models.app_setting",
        "app.models.auth_session",
        "app.models.document",
        "app.models.document_profile",
        "app.models.document_progress",
        "app.models.friendship",
        "app.models.job",
        "app.models.playback_session",
        "app.models.section",
        "app.models.shared_item",
        "app.models.text_chunk",
        "app.models.user",
        "app.models.user_invite",
        "app.models.user_setting",
        "app.models.voice_preset",
    ):
        reload(import_module(module_name))

    reload(import_module("app.db"))
    reload(import_module("app.services.auth"))
    reload(import_module("app.api.auth"))

    main_module = import_module("app.main")
    return reload(main_module).app


def _bootstrap_admin(client: TestClient) -> None:
    response = client.post(
        "/api/auth/bootstrap-admin",
        json={
            "username": "admin",
            "display_name": "Admin User",
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201


def _create_user(*, username: str, display_name: str, password: str) -> int:
    db_module = import_module("app.db")
    auth_service = import_module("app.services.auth")

    with db_module.session_scope() as session:
        user = auth_service.create_user(
            session,
            username=username,
            display_name=display_name,
            password=password,
        )
        return user.id


def _login(client: TestClient, *, username: str, password: str) -> int:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["user"]["id"]


@pytest.fixture()
def admin_and_member(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'admin.db'}")

    app = _load_app()

    with TestClient(app) as admin_client, TestClient(app) as member_client:
        _bootstrap_admin(admin_client)
        member_user_id = _create_user(
            username="member", display_name="Member User", password="member-password-123"
        )
        _login(member_client, username="member", password="member-password-123")
        yield admin_client, member_client, member_user_id


def test_members_cannot_use_admin_endpoints(admin_and_member) -> None:
    _admin_client, member_client, member_user_id = admin_and_member

    assert member_client.get("/api/auth/users").status_code == 403
    assert (
        member_client.patch(f"/api/auth/users/{member_user_id}", json={"role": "admin"}).status_code == 403
    )
    assert member_client.post(f"/api/auth/users/{member_user_id}/reset-password").status_code == 403
    assert member_client.post(f"/api/auth/users/{member_user_id}/revoke-sessions").status_code == 403


def test_users_list_includes_account_stats(admin_and_member) -> None:
    admin_client, _member_client, _member_user_id = admin_and_member

    users = admin_client.get("/api/auth/users").json()
    assert {user["username"] for user in users} == {"admin", "member"}
    for user in users:
        assert "documents_count" in user
        assert "voice_presets_count" in user
        assert "jobs_count" in user
        assert "storage_bytes" in user
        assert user["created_at"] is not None


def test_admin_can_change_role_but_not_their_own(admin_and_member) -> None:
    admin_client, _member_client, member_user_id = admin_and_member

    promote_response = admin_client.patch(f"/api/auth/users/{member_user_id}", json={"role": "admin"})
    assert promote_response.status_code == 200
    assert promote_response.json()["role"] == "admin"

    demote_response = admin_client.patch(f"/api/auth/users/{member_user_id}", json={"role": "member"})
    assert demote_response.status_code == 200
    assert demote_response.json()["role"] == "member"

    invalid_role_response = admin_client.patch(
        f"/api/auth/users/{member_user_id}", json={"role": "owner"}
    )
    assert invalid_role_response.status_code == 422

    admin_user_id = admin_client.get("/api/auth/me").json()["id"]
    self_response = admin_client.patch(f"/api/auth/users/{admin_user_id}", json={"role": "member"})
    assert self_response.status_code == 422


def test_disabling_a_user_revokes_access_immediately(admin_and_member) -> None:
    admin_client, member_client, member_user_id = admin_and_member

    assert member_client.get("/api/auth/me").status_code == 200

    disable_response = admin_client.patch(
        f"/api/auth/users/{member_user_id}", json={"status": "disabled"}
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["status"] == "disabled"

    assert member_client.get("/api/auth/me").status_code == 401

    relogin_response = member_client.post(
        "/api/auth/login",
        json={"username": "member", "password": "member-password-123"},
    )
    assert relogin_response.status_code == 401

    enable_response = admin_client.patch(
        f"/api/auth/users/{member_user_id}", json={"status": "active"}
    )
    assert enable_response.status_code == 200
    assert (
        member_client.post(
            "/api/auth/login",
            json={"username": "member", "password": "member-password-123"},
        ).status_code
        == 200
    )


def test_admin_password_reset_rotates_credentials(admin_and_member) -> None:
    admin_client, member_client, member_user_id = admin_and_member

    reset_response = admin_client.post(f"/api/auth/users/{member_user_id}/reset-password")
    assert reset_response.status_code == 200
    temporary_password = reset_response.json()["temporary_password"]
    assert len(temporary_password) >= settings.auth_password_min_length

    assert member_client.get("/api/auth/me").status_code == 401

    old_password_response = member_client.post(
        "/api/auth/login",
        json={"username": "member", "password": "member-password-123"},
    )
    assert old_password_response.status_code == 401

    new_password_response = member_client.post(
        "/api/auth/login",
        json={"username": "member", "password": temporary_password},
    )
    assert new_password_response.status_code == 200


def test_admin_can_revoke_sessions(admin_and_member) -> None:
    admin_client, member_client, member_user_id = admin_and_member

    assert member_client.get("/api/auth/me").status_code == 200

    revoke_response = admin_client.post(f"/api/auth/users/{member_user_id}/revoke-sessions")
    assert revoke_response.status_code == 200
    assert revoke_response.json()["revoked_sessions"] >= 1

    assert member_client.get("/api/auth/me").status_code == 401
