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
        "app.models.collection",
        "app.models.document",
        "app.models.document_profile",
        "app.models.document_progress",
        "app.models.job",
        "app.models.playback_session",
        "app.models.section",
        "app.models.text_chunk",
        "app.models.voice_preset",
    ):
        reload(import_module(module_name))

    reload(import_module("app.db"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.services.collections"))
    reload(import_module("app.api.collections"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_collections_api_creates_collection_and_manages_membership(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    create_response = client.post(
        "/api/collections",
        json={"name": "Favorites", "description": "Alice's keepers"},
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["name"] == "Favorites"
    assert payload["description"] == "Alice's keepers"
    assert payload["document_count"] == 0
    assert payload["documents"] == []

    add_response = client.post(
        f"/api/collections/{payload['id']}/documents",
        json={"document_id": import_response.json()["id"]},
    )
    assert add_response.status_code == 200
    assert add_response.json()["document_count"] == 1
    assert add_response.json()["documents"][0]["id"] == import_response.json()["id"]

    list_response = client.get("/api/collections")
    assert list_response.status_code == 200
    assert list_response.json()[0]["document_count"] == 1

    remove_response = client.delete(
        f"/api/collections/{payload['id']}/documents/{import_response.json()['id']}"
    )
    assert remove_response.status_code == 204

    refreshed_response = client.get("/api/collections")
    assert refreshed_response.status_code == 200
    assert refreshed_response.json()[0]["document_count"] == 0
