from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
import app.services.catalogs as catalogs
from app.services.book_metadata import ExternalMetadata
from app.services.documents import ExternalSourceProvenance


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
    reload(import_module("app.api.documents"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_catalog_sources_route_lists_shipped_catalogs(client: TestClient) -> None:
    response = client.get("/api/catalogs/sources")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "gutenberg",
            "name": "Project Gutenberg",
            "description": "Public-domain ebooks discovered through Gutenberg and Gutendex.",
            "supports_search": True,
            "supports_browse": True,
        },
        {
            "id": "standard_ebooks",
            "name": "Standard Ebooks",
            "description": "Carefully produced public-domain ebook editions from Standard Ebooks.",
            "supports_search": True,
            "supports_browse": True,
        },
        {
            "id": "openlibrary",
            "name": "Open Library / Internet Archive",
            "description": "Public full-text works discovered in Open Library and imported from Internet Archive.",
            "supports_search": True,
            "supports_browse": False,
        },
    ]


def test_gutenberg_top_route_returns_normalized_ui_ready_results(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.api.catalogs.catalogs_service.browse_gutenberg_catalog",
        lambda limit=12: [
            catalogs.CatalogResultRecord(
                id="84",
                source="gutenberg",
                source_name="Project Gutenberg",
                title="Frankenstein",
                author="Mary Shelley",
                summary="A scientist creates a monster.",
                cover_url="https://example.test/frankenstein.jpg",
                detail_url="https://www.gutenberg.org/ebooks/84",
                download_format="epub",
                language="en",
                importable=True,
            )
        ],
    )

    response = client.get("/api/catalogs/gutenberg/top?limit=1")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "84",
            "source": "gutenberg",
            "source_name": "Project Gutenberg",
            "title": "Frankenstein",
            "author": "Mary Shelley",
            "summary": "A scientist creates a monster.",
            "cover_url": "https://example.test/frankenstein.jpg",
            "detail_url": "https://www.gutenberg.org/ebooks/84",
            "download_format": "epub",
            "language": "en",
            "importable": True,
        }
    ]


def test_catalog_import_route_uses_canonical_pipeline_and_persists_source_provenance(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_import_catalog_item(source: str, catalog_id: str, owner_user_id: int | None = None):
        assert source == "gutenberg"
        assert catalog_id == "84"
        assert owner_user_id == 1
        from app.services.documents import import_external_document

        return import_external_document(
            filename="frankenstein.txt",
            file_bytes=b"Frankenstein body text.",
            metadata_hint=ExternalMetadata(
                title="Frankenstein",
                author="Mary Shelley",
                description="A scientist creates a monster.",
                metadata_source="gutendex",
                metadata_source_id="84",
                exact_match=True,
            ),
            source_provenance=ExternalSourceProvenance(
                provider="gutenberg",
                provider_id="84",
                provider_name="Project Gutenberg",
                provider_url="https://www.gutenberg.org/ebooks/84",
            ),
            owner_user_id=owner_user_id,
        )

    monkeypatch.setattr("app.api.catalogs.catalogs_service.import_catalog_item", fake_import_catalog_item)

    response = client.post("/api/catalogs/import", json={"source": "gutenberg", "catalog_id": "84"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Frankenstein"
    assert payload["format"] == "txt"
    assert payload["summary"] == "A scientist creates a monster."
    assert payload["source_provider"] == "gutenberg"
    assert payload["source_provider_name"] == "Project Gutenberg"
    assert payload["source_provider_url"] == "https://www.gutenberg.org/ebooks/84"

    detail_response = client.get(f"/api/documents/{payload['id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["summary"] == "A scientist creates a monster."
    assert detail_payload["source_provider"] == "gutenberg"
    assert detail_payload["source_provider_name"] == "Project Gutenberg"
    assert detail_payload["sections"][0]["preview_text"] == "Frankenstein body text."
