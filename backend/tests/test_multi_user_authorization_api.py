from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings

SHORT_SAMPLE_TEXT = "First sentence. Second sentence."


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    for module_name in (
        "app.models.app_setting",
        "app.models.auth_session",
        "app.models.collection",
        "app.models.document",
        "app.models.document_profile",
        "app.models.document_progress",
        "app.models.job",
        "app.models.playback_session",
        "app.models.section",
        "app.models.text_chunk",
        "app.models.theme_profile",
        "app.models.user",
        "app.models.user_invite",
        "app.models.user_setting",
        "app.models.voice_preset",
    ):
        reload(import_module(module_name))

    reload(import_module("app.db"))
    reload(import_module("app.services.auth"))
    reload(import_module("app.services.collections"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.jobs"))
    reload(import_module("app.services.library_view"))
    reload(import_module("app.services.playback"))
    reload(import_module("app.services.settings"))
    reload(import_module("app.services.themes"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.auth"))
    reload(import_module("app.api.collections"))
    reload(import_module("app.api.documents"))
    reload(import_module("app.api.jobs"))
    reload(import_module("app.api.playback"))
    reload(import_module("app.api.settings"))
    reload(import_module("app.api.themes"))
    reload(import_module("app.api.voices"))

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


def _create_user(*, username: str, display_name: str, password: str) -> None:
    db_module = import_module("app.db")
    auth_service = import_module("app.services.auth")

    with db_module.session_scope() as session:
        auth_service.create_user(
            session,
            username=username,
            display_name=display_name,
            password=password,
        )


def _login(client: TestClient, *, username: str, password: str) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200


def _import_document(client: TestClient, *, filename: str = "sample.txt", body: bytes | None = None) -> dict:
    response = client.post(
        "/api/documents/import",
        files={"file": (filename, body or SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture()
def client_trio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, TestClient, TestClient]:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'multi-user-authz.db'}")

    app = _load_app()

    with TestClient(app) as anonymous_client, TestClient(app) as admin_client, TestClient(app) as member_client:
        _bootstrap_admin(admin_client)
        _create_user(
            username="member",
            display_name="Member User",
            password="member password 123",
        )
        _login(member_client, username="member", password="member password 123")
        yield anonymous_client, admin_client, member_client


def test_user_owned_routes_require_authentication(client_trio: tuple[TestClient, TestClient, TestClient]) -> None:
    anonymous_client, _admin_client, _member_client = client_trio

    for path in (
        "/api/documents",
        "/api/documents/summary",
        "/api/jobs",
        "/api/collections",
        "/api/settings",
        "/api/themes",
        "/api/voices/presets",
    ):
        response = anonymous_client.get(path)
        assert response.status_code == 401


def test_documents_and_playback_are_scoped_to_the_current_user(
    client_trio: tuple[TestClient, TestClient, TestClient],
) -> None:
    _anonymous_client, admin_client, member_client = client_trio
    admin_document = _import_document(admin_client)

    playback_response = admin_client.post(
        "/api/playback/sessions",
        json={"document_id": admin_document["id"]},
    )
    assert playback_response.status_code == 201
    playback_session_id = playback_response.json()["id"]

    member_documents = member_client.get("/api/documents")
    assert member_documents.status_code == 200
    assert member_documents.json() == []

    direct_document = member_client.get(f"/api/documents/{admin_document['id']}")
    assert direct_document.status_code == 404

    create_playback = member_client.post(
        "/api/playback/sessions",
        json={"document_id": admin_document["id"]},
    )
    assert create_playback.status_code == 404

    get_playback = member_client.get(f"/api/playback/sessions/{playback_session_id}")
    assert get_playback.status_code == 404

    get_audio = member_client.get(f"/api/playback/audio/{playback_session_id}")
    assert get_audio.status_code == 404

    prebuffer_playback = member_client.post(f"/api/playback/sessions/{playback_session_id}/prebuffer")
    assert prebuffer_playback.status_code == 404


def test_jobs_collections_themes_and_presets_are_scoped_to_the_current_user(
    client_trio: tuple[TestClient, TestClient, TestClient],
) -> None:
    _anonymous_client, admin_client, member_client = client_trio
    admin_document = _import_document(admin_client)

    collection_response = admin_client.post(
        "/api/collections",
        json={"name": "Favorites", "description": "Admin shelf"},
    )
    assert collection_response.status_code == 201
    collection_id = collection_response.json()["id"]

    add_document_response = admin_client.post(
        f"/api/collections/{collection_id}/documents",
        json={"document_id": admin_document["id"]},
    )
    assert add_document_response.status_code == 200

    preset_response = admin_client.post(
        "/api/voices/presets",
        data={"name": "Warm Narrator", "transcript": "A warm sample transcript."},
        files={"reference_audio": ("warm.wav", b"RIFFdemo", "audio/wav")},
    )
    assert preset_response.status_code == 201

    theme_response = admin_client.post(
        "/api/themes",
        json={
            "name": "Aurora",
            "description": "Admin imported theme.",
            "source_kind": "imported",
            "source_label": "Unit test",
            "source_reference": "unit-test",
            "tokens": {
                "--color-bg": "#0a1118",
                "--color-accent": "#9ad7ff",
            },
        },
    )
    assert theme_response.status_code == 201

    job_response = admin_client.post(
        "/api/jobs/export",
        json={
            "document_id": admin_document["id"],
            "voice_preset_id": "default",
            "format": "wav",
        },
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]

    member_collections = member_client.get("/api/collections")
    assert member_collections.status_code == 200
    assert member_collections.json() == []

    member_presets = member_client.get("/api/voices/presets")
    assert member_presets.status_code == 200
    assert member_presets.json() == []

    member_jobs = member_client.get("/api/jobs")
    assert member_jobs.status_code == 200
    assert member_jobs.json() == []

    member_job_detail = member_client.get(f"/api/jobs/{job_id}")
    assert member_job_detail.status_code == 404

    member_themes = member_client.get("/api/themes")
    assert member_themes.status_code == 200
    theme_ids = [theme["id"] for theme in member_themes.json()]
    assert "ember" in theme_ids
    assert "aurora" not in theme_ids


def test_settings_are_isolated_per_user(client_trio: tuple[TestClient, TestClient, TestClient]) -> None:
    _anonymous_client, admin_client, member_client = client_trio

    admin_settings = admin_client.get("/api/settings")
    assert admin_settings.status_code == 200

    admin_update = admin_client.put(
        "/api/settings",
        json={
            **admin_settings.json(),
            "active_theme_id": "ocean",
            "ui_theme": "ocean",
            "default_playback_speed": 1.55,
            "tooltips_enabled": False,
        },
    )
    assert admin_update.status_code == 200

    member_settings = member_client.get("/api/settings")
    assert member_settings.status_code == 200
    member_payload = member_settings.json()
    assert member_payload["active_theme_id"] == "ember"
    assert member_payload["default_playback_speed"] == 1.0
    assert member_payload["tooltips_enabled"] is True

    member_update = member_client.put(
        "/api/settings",
        json={
            **member_payload,
            "active_theme_id": "forest",
            "ui_theme": "forest",
            "default_playback_speed": 1.25,
        },
    )
    assert member_update.status_code == 200

    refreshed_admin_settings = admin_client.get("/api/settings")
    assert refreshed_admin_settings.status_code == 200
    assert refreshed_admin_settings.json()["active_theme_id"] == "ocean"
    assert refreshed_admin_settings.json()["default_playback_speed"] == 1.55
