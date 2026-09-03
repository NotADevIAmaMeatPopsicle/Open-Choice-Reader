from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.theme_profile"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.settings"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.playback"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.services.themes"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.settings"))
    reload(import_module("app.api.playback"))
    reload(import_module("app.api.themes"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_get_settings_returns_reader_preference_defaults(client: TestClient) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_theme_id"] == "ember"
    assert payload["active_theme"]["id"] == "ember"
    assert payload["active_theme"]["source_kind"] == "house"
    assert payload["ui_theme"] == "ember"
    assert payload["sidebar_width_px"] == 196
    assert payload["sidebar_mode"] == "expanded"
    assert payload["dock_position"] == "bottom"
    assert payload["tooltips_enabled"] is True
    assert payload["default_playback_speed"] == 1.0
    assert payload["auto_pause_on_interrupt"] is True
    assert payload["library_view_mode"] == "cover"
    assert payload["background_override_theme_id"] is None
    assert payload["shelf_override_theme_id"] is None


def test_update_settings_persists_reader_preferences(client: TestClient) -> None:
    existing = client.get("/api/settings")
    assert existing.status_code == 200
    existing_payload = existing.json()

    response = client.put(
        "/api/settings",
        json={
            **existing_payload,
            "ui_theme": "ocean",
            "sidebar_width_px": 96,
            "sidebar_mode": "compact",
            "dock_position": "top-center",
            "tooltips_enabled": False,
            "default_playback_speed": 1.55,
            "auto_pause_on_interrupt": False,
            "library_view_mode": "spine",
            "background_override_theme_id": "ocean",
            "shelf_override_theme_id": "forest",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ui_theme"] == "ocean"
    assert payload["active_theme_id"] == "ocean"
    assert payload["active_theme"]["id"] == "ocean"
    assert payload["sidebar_width_px"] == 196
    assert payload["sidebar_mode"] == "expanded"
    assert payload["dock_position"] == "top-center"
    assert payload["tooltips_enabled"] is False
    assert payload["default_playback_speed"] == 1.55
    assert payload["auto_pause_on_interrupt"] is False
    assert payload["library_view_mode"] == "spine"
    assert payload["background_override_theme_id"] == "ocean"
    assert payload["shelf_override_theme_id"] == "forest"

    refetch = client.get("/api/settings")
    assert refetch.status_code == 200
    assert refetch.json()["default_playback_speed"] == 1.55
    assert refetch.json()["sidebar_mode"] == "expanded"


def test_update_settings_persists_and_clamps_live_narration_pace(client: TestClient) -> None:
    existing = client.get("/api/settings")
    assert existing.status_code == 200
    assert existing.json()["live_narration_pace"] == 1.0

    response = client.put(
        "/api/settings",
        json={**existing.json(), "live_narration_pace": 1.5},
    )
    assert response.status_code == 200
    assert response.json()["live_narration_pace"] == 1.5

    refetch = client.get("/api/settings")
    assert refetch.status_code == 200
    assert refetch.json()["live_narration_pace"] == 1.5

    clamped = client.put(
        "/api/settings",
        json={**refetch.json(), "live_narration_pace": 5.0},
    )
    assert clamped.status_code == 200
    assert clamped.json()["live_narration_pace"] == 2.0


def test_create_playback_session_uses_saved_default_speed(client: TestClient) -> None:
    settings_response = client.get("/api/settings")
    assert settings_response.status_code == 200

    update_response = client.put(
        "/api/settings",
        json={
            **settings_response.json(),
            "default_playback_speed": 1.65,
        },
    )
    assert update_response.status_code == 200

    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"First sentence. Second sentence.", "text/plain")},
    )
    assert import_response.status_code == 201

    playback_response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )

    assert playback_response.status_code == 201
    assert playback_response.json()["playback_speed"] == 1.65
