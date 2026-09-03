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


def test_list_themes_returns_seeded_profiles(client: TestClient) -> None:
    response = client.get("/api/themes")

    assert response.status_code == 200
    payload = response.json()
    assert [theme["id"] for theme in payload[:3]] == ["ember", "ocean", "forest"]
    assert payload[0]["source_kind"] == "house"
    assert "tokens" in payload[0]


def test_list_themes_exposes_showcase_metadata_fields(client: TestClient) -> None:
    response = client.get("/api/themes")

    assert response.status_code == 200
    payload = response.json()
    first_theme = payload[0]
    assert "family" in first_theme
    assert "preview_variant" in first_theme
    assert "background_asset_path" in first_theme
    assert "background_overlay_path" in first_theme
    assert "shelf_asset_path" in first_theme
    assert "surface_texture_asset_path" in first_theme
    assert "supports_mix_and_match" in first_theme


def test_apply_theme_updates_active_theme_in_settings(client: TestClient) -> None:
    response = client.post("/api/themes/ocean/apply")

    assert response.status_code == 200
    assert response.json()["active_theme_id"] == "ocean"

    settings_response = client.get("/api/settings")
    assert settings_response.status_code == 200
    assert settings_response.json()["active_theme_id"] == "ocean"
    assert settings_response.json()["active_theme"]["id"] == "ocean"


def test_create_and_delete_custom_theme(client: TestClient) -> None:
    create_response = client.post(
        "/api/themes",
        json={
            "name": "Aurora",
            "description": "A bright imported test theme.",
            "source_kind": "imported",
            "source_label": "Test import",
            "source_reference": "unit-test",
            "tokens": {
                "--color-bg": "#0a1118",
                "--color-accent": "#9ad7ff",
            },
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == "aurora"
    assert created["source_kind"] == "imported"

    list_response = client.get("/api/themes")
    assert list_response.status_code == 200
    assert any(theme["id"] == "aurora" for theme in list_response.json())

    delete_response = client.delete("/api/themes/aurora")
    assert delete_response.status_code == 204

    refetch_response = client.get("/api/themes")
    assert refetch_response.status_code == 200
    assert all(theme["id"] != "aurora" for theme in refetch_response.json())


def test_import_kavita_theme_from_pasted_css_returns_created_theme_and_report(client: TestClient) -> None:
    response = client.post(
        "/api/themes/import/kavita",
        data={
            "name": "Midnight Harbor",
            "css_text": """
            :root .bg-midnight-harbor {
              --primary-color: #68b7ff;
              --primary-color-dark-shade: #245d91;
              --bs-body-bg: #0b1118;
              --body-text-color: #eef5fb;
              --text-muted-color: #9fb5c7;
              --navbar-bg-color: #162636;
              --unsupported-token: #ffffff;
            }
            """,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["theme"]["id"] == "midnight-harbor"
    assert payload["theme"]["source_kind"] == "imported_kavita"
    assert payload["report"]["detected_variable_count"] == 7
    assert any(
        item["source_variable"] == "--primary-color" and item["target_token"] == "--color-accent"
        for item in payload["report"]["mapped_variables"]
    )
    assert "--unsupported-token" in payload["report"]["ignored_variables"]


def test_import_kavita_theme_from_uploaded_file_returns_created_theme_and_report(client: TestClient) -> None:
    response = client.post(
        "/api/themes/import/kavita",
        files={
            "css_file": (
                "harbor-night.css",
                b"""
                :root .bg-harbor-night {
                  --primary-color: #7ad0ff;
                  --bs-body-bg: #081018;
                  --body-text-color: #f1f7fb;
                  --navbar-bg-color: #142535;
                }
                """,
                "text/css",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["theme"]["id"] == "harbor-night"
    assert payload["theme"]["source_reference"] == "harbor-night.css"
    assert payload["report"]["detected_variable_count"] == 4
    assert payload["report"]["mapped_variables"]
