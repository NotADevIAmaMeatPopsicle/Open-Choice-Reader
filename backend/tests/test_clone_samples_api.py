from importlib import import_module, reload
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import settings


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.auth_session"))
    reload(import_module("app.models.user"))
    reload(import_module("app.models.user_invite"))
    reload(import_module("app.models.user_setting"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.auth"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.services.clone_sample_sources"))
    reload(import_module("app.api.auth"))
    reload(import_module("app.api.clone_samples"))

    main_module = import_module("app.main")
    return reload(main_module).app


def test_clone_sample_import_creates_current_user_voice_preset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    app = _load_app()

    remote_fetch = import_module("app.services.remote_fetch")
    monkeypatch.setattr(
        "app.api.clone_samples.fetch_remote_resource",
        lambda *args, **kwargs: remote_fetch.RemoteResource(
            final_url="https://archive.org/download/sample/chapter1.mp3",
            content_type="audio/mpeg",
            headers={"content-type": "audio/mpeg"},
            body=b"ID3voice",
        ),
    )

    with TestClient(app) as client:
        bootstrap_response = client.post(
            "/api/auth/bootstrap-admin",
            json={
                "username": "admin",
                "display_name": "Admin User",
                "password": "admin-password-123",
            },
        )
        assert bootstrap_response.status_code == 201

        response = client.post(
            "/api/clone-samples/import",
            json={
                "provider": "librivox",
                "title": "Public Domain Reading - Chapter 1",
                "speaker": "Ada Reader",
                "audio_url": "https://archive.org/download/sample/chapter1.mp3",
                "transcript": "Reviewed transcript text.",
                "transcript_source_url": "https://www.gutenberg.org/ebooks/123",
                "source_url": "https://librivox.org/public-domain-reading/",
                "license_label": "Public domain",
                "provenance_note": "Reviewed by operator.",
            },
        )

    assert response.status_code == 201
    assert response.json()["name"] == "Public Domain Reading - Chapter 1"
    assert response.json()["source_provider"] == "librivox"

    db = import_module("app.db")
    voice_model = import_module("app.models.voice_preset")
    with db.session_scope() as session:
        preset = session.get(voice_model.VoicePreset, response.json()["id"])
        assert preset.owner_user_id == bootstrap_response.json()["user"]["id"]
        assert preset.source_url == "https://librivox.org/public-domain-reading/"
