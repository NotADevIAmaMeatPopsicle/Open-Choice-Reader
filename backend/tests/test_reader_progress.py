from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings

SHORT_SAMPLE_TEXT = "First sentence. Second sentence."
LONG_SAMPLE_TEXT = " ".join(
    [
        "Alice reads a steady paragraph that keeps the passage coherent and easy to follow."
        for _ in range(28)
    ]
)


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.settings"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.playback"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.api.playback"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_patch_playback_session_updates_progress(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert session_response.status_code == 201

    response = client.patch(
        f"/api/playback/sessions/{session_response.json()['id']}",
        json={"current_chunk_index": 1},
    )

    assert response.status_code == 200
    assert response.json()["id"] == session_response.json()["id"]
    assert response.json()["current_chunk_index"] == 1


def test_patch_playback_session_rejects_out_of_range_progress(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert session_response.status_code == 201

    response = client.patch(
        f"/api/playback/sessions/{session_response.json()['id']}",
        json={"current_chunk_index": 99},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Chunk index 99 is out of range for playback session 1"


def test_patch_playback_session_updates_library_progress_summary(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert session_response.status_code == 201

    response = client.patch(
        f"/api/playback/sessions/{session_response.json()['id']}",
        json={"current_chunk_index": 1},
    )

    assert response.status_code == 200

    document_response = client.get("/api/documents")
    assert document_response.status_code == 200

    [document] = document_response.json()
    assert document["current_chunk_index"] == 1
    assert document["progress_percent"] > 0
    assert document["last_opened_at"] is not None
