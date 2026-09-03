from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.services.user_storage import user_source_root


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.app_setting"))
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.documents"))
    reload(import_module("app.services.catalogs"))
    reload(import_module("app.api.catalogs"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_import_url_route_downloads_supported_file_and_persists_provenance(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalogs_service = import_module("app.services.catalogs")

    monkeypatch.setattr(
        catalogs_service,
        "_fetch_remote_asset",
        lambda url: catalogs_service.RemoteAssetRecord(
            requested_url=url,
            final_url=url,
            content_type="text/plain",
            filename="open-choice.txt",
            body=b"Open Choice Reader can import this text file.",
        ),
    )

    response = client.post(
        "/api/catalogs/import-url",
        json={"url": "https://example.test/open-choice.txt"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "open-choice"
    assert payload["format"] == "txt"
    assert payload["source_provider"] == "url"
    assert payload["source_provider_name"] == "Direct URL import"
    assert payload["source_url"] == "https://example.test/open-choice.txt"
    assert payload["source_site_name"] == "example.test"
    assert payload["import_mode"] == "direct_url"


def test_import_url_route_extracts_article_snapshot_and_source_metadata(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalogs_service = import_module("app.services.catalogs")

    monkeypatch.setattr(
        catalogs_service,
        "_fetch_remote_asset",
        lambda url: catalogs_service.RemoteAssetRecord(
            requested_url=url,
            final_url=url,
            content_type="text/html",
            filename=None,
            body=b"<html><head><title>Ignored shell</title></head><body><nav>noise</nav><article><h1>Readable article</h1><p>Article body for import.</p></article></body></html>",
        ),
    )
    monkeypatch.setattr(
        catalogs_service,
        "_extract_article_snapshot",
        lambda html, url: catalogs_service.ArticleSnapshotRecord(
            title="Readable article",
            author="Open Writer",
            summary="Article body for import.",
            cleaned_html="<html><head><title>Readable article</title></head><body><article><h1>Readable article</h1><p>Article body for import.</p></article></body></html>",
        ),
    )

    response = client.post(
        "/api/catalogs/import-url",
        json={"url": "https://example.test/articles/open-choice"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Readable article"
    assert payload["author"] == "Open Writer"
    assert payload["format"] == "html"
    assert payload["summary"] == "Article body for import."
    assert payload["source_provider"] == "web"
    assert payload["source_provider_name"] == "Article import"
    assert payload["source_url"] == "https://example.test/articles/open-choice"
    assert payload["source_site_name"] == "example.test"
    assert payload["import_mode"] == "article_url"


def test_import_text_route_creates_markdown_snapshot_and_source_metadata(client: TestClient) -> None:
    response = client.post(
        "/api/catalogs/import-text",
        json={
            "title": "Reader note",
            "author": "Casey Example",
            "body": "This is pasted in from somewhere else.\n\nIt should import like a real item.",
            "source_url": "https://notes.example.test/open-choice-reader",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Reader note"
    assert payload["author"] == "Casey Example"
    assert payload["format"] == "md"
    assert payload["source_provider"] == "manual"
    assert payload["source_provider_name"] == "Pasted text"
    assert payload["source_url"] == "https://notes.example.test/open-choice-reader"
    assert payload["source_site_name"] == "notes.example.test"
    assert payload["import_mode"] == "pasted_text"

    stored_files = list(user_source_root(1).glob("reader-note*.md"))
    assert len(stored_files) == 1
    stored_content = stored_files[0].read_text(encoding="utf-8")
    assert "# Reader note" in stored_content
    assert "This is pasted in from somewhere else." in stored_content
    assert "Source URL: https://notes.example.test/open-choice-reader" in stored_content
