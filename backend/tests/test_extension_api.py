from importlib import import_module, reload
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

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
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.settings"))
    reload(import_module("app.services.documents"))
    reload(import_module("app.api.settings"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_download_chromium_extension_bundle(client: TestClient) -> None:
    response = client.get("/api/extension/chromium")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment;" in response.headers["content-disposition"]
    assert "open-choice-reader-chromium-extension.zip" in response.headers["content-disposition"]

    archive = ZipFile(BytesIO(response.content))
    names = set(archive.namelist())

    assert "manifest.json" in names
    assert "popup.html" in names
    assert "popup.css" in names
    assert "popup.js" in names
    assert "background.js" in names
    assert "core.js" in names
    assert "README.md" in names
