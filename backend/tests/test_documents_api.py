from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import Headers, UploadFile

from app.config import settings
from app.services.user_storage import user_inbox_root, user_source_root

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
    reload(import_module("app.models.playback_session"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    reload(import_module("app.services.settings"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.tts.registry"))
    reload(import_module("app.services.playback"))
    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_import_upload_creates_document_row(client: TestClient) -> None:
    response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "sample"
    assert payload["format"] == "txt"
    assert payload["status"] == "uploaded"
    assert payload["author"] is None
    assert payload["cover_url"] == f"/api/documents/{payload['id']}/cover"
    assert payload["summary"] == "hello world"
    assert payload["total_sections"] == 1
    assert payload["total_chunks"] == 1
    assert payload["estimated_duration_seconds"] >= 1
    assert payload["current_chunk_index"] is None
    assert payload["progress_percent"] == 0
    assert payload["last_opened_at"] is None
    assert "source_path" not in payload

    documents_response = client.get("/api/documents")
    assert documents_response.status_code == 200
    documents = documents_response.json()
    assert len(documents) == 1
    assert documents[0]["title"] == "sample"
    assert documents[0]["format"] == "txt"
    assert documents[0]["status"] == "uploaded"
    assert documents[0]["cover_url"] == f"/api/documents/{payload['id']}/cover"
    assert "source_path" not in documents[0]


def test_import_epub_uses_embedded_metadata_and_cover(client: TestClient, epub_fixture_bytes: bytes) -> None:
    response = client.post(
        "/api/documents/import",
        files={"file": ("fixture.epub", epub_fixture_bytes, "application/epub+zip")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Alice Fixture"
    assert payload["author"] == "Fixture Author"
    assert payload["summary"] == "Alice's fixture description."
    assert payload["cover_url"] == f"/api/documents/{payload['id']}/cover"
    assert payload["total_sections"] == 1
    assert payload["total_chunks"] >= 1

    cover_response = client.get(payload["cover_url"])

    assert cover_response.status_code == 200
    assert cover_response.headers["content-type"].startswith("image/svg+xml")
    assert b"Fixture Cover" in cover_response.content


def test_import_html_extracts_title_author_and_content(client: TestClient) -> None:
    response = client.post(
        "/api/documents/import",
        files={
            "file": (
                "fixture.html",
                b"""<!DOCTYPE html><html><head><title>Spoon River Anthology</title></head><body><p>Author: Edgar Lee Masters</p><h1>Spoon River Anthology</h1><p>Poem one.</p></body></html>""",
                "text/html",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Spoon River Anthology"
    assert payload["author"] == "Edgar Lee Masters"
    assert payload["format"] == "html"
    assert "Poem one." in payload["summary"]


def test_inbox_listing_returns_files_from_inbox_root(
    client: TestClient, tmp_path: Path
) -> None:
    inbox_file = user_inbox_root(1) / "incoming.txt"
    inbox_file.parent.mkdir(parents=True, exist_ok=True)
    inbox_file.write_text("from inbox", encoding="utf-8")

    response = client.get("/api/documents/inbox")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "incoming.txt"
    assert payload[0]["format"] == "txt"
    assert payload[0]["document_id"] is None


def test_import_inbox_candidate_creates_document_row(client: TestClient) -> None:
    inbox_file = user_inbox_root(1) / "incoming.md"
    inbox_file.parent.mkdir(parents=True, exist_ok=True)
    inbox_file.write_text("# Inbox Title\nFirst paragraph.", encoding="utf-8")

    response = client.post("/api/documents/import-inbox", json={"path": "incoming.md"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Inbox Title"
    assert payload["format"] == "md"
    assert payload["status"] == "uploaded"

    inbox_response = client.get("/api/documents/inbox")
    assert inbox_response.status_code == 200
    inbox_payload = inbox_response.json()
    assert inbox_payload[0]["document_id"] == payload["id"]


def test_reimport_document_refreshes_changed_source_file(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.md", b"# Chapter One\nFirst paragraph.", "text/markdown")},
    )
    assert import_response.status_code == 201

    stored_file = next(user_source_root(1).glob("sample*.md"))
    stored_file.write_text("# Chapter One\nUpdated paragraph.\n\n# Chapter Two\nFresh chapter.", encoding="utf-8")

    response = client.post(f"/api/documents/{import_response.json()['id']}/reimport")

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Chapter One"
    assert payload["total_sections"] == 2
    assert payload["current_chunk_index"] is None

    detail_response = client.get(f"/api/documents/{import_response.json()['id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert [section["title"] for section in detail_payload["sections"]] == ["Chapter One", "Chapter Two"]
    assert detail_payload["summary"] == "Updated paragraph."


def test_document_listing_returns_imported_rows(client: TestClient) -> None:
    create_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert create_response.status_code == 201

    response = client.get("/api/documents")

    assert response.status_code == 200
    payload = response.json()
    assert [document["title"] for document in payload] == ["sample"]


def test_document_summary_returns_recent_and_continue_reading_rows(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201

    playback_session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": import_response.json()["id"]},
    )
    assert playback_session_response.status_code == 201

    progress_response = client.patch(
        f"/api/playback/sessions/{playback_session_response.json()['id']}",
        json={"current_chunk_index": 1},
    )
    assert progress_response.status_code == 200

    response = client.get("/api/documents/summary")

    assert response.status_code == 200
    payload = response.json()
    assert [document["id"] for document in payload["recent_documents"]] == [import_response.json()["id"]]
    assert [document["id"] for document in payload["continue_reading"]] == [import_response.json()["id"]]
    assert payload["continue_reading"][0]["current_chunk_index"] == 1
    assert payload["continue_reading"][0]["progress_percent"] > 0
    assert payload["continue_reading"][0]["last_opened_at"] is not None


def test_document_detail_returns_sections_for_book_navigation(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={
            "file": (
                "book.md",
                b"# Chapter One\nFirst section opening.\n\n# Chapter Two\nSecond section opening.",
                "text/markdown",
            )
        },
    )
    assert import_response.status_code == 201

    detail_response = client.get(f"/api/documents/{import_response.json()['id']}")

    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["title"] == "Chapter One"
    assert payload["total_sections"] == 2
    assert payload["sections"] == [
        {
            "id": 1,
            "position": 0,
            "title": "Chapter One",
            "chunk_start_index": 0,
            "chunk_count": 1,
            "preview_text": "First section opening.",
        },
        {
            "id": 2,
            "position": 1,
            "title": "Chapter Two",
            "chunk_start_index": 1,
            "chunk_count": 1,
            "preview_text": "Second section opening.",
        },
    ]


def test_duplicate_uploads_use_distinct_stored_files(client: TestClient) -> None:
    first_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"first version", "text/plain")},
    )
    second_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"second version", "text/plain")},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    stored_files = sorted(user_source_root(1).glob("sample*"))

    assert len(stored_files) == 2
    assert stored_files[0] != stored_files[1]
    contents = {path.read_text(encoding="utf-8") for path in stored_files}
    assert contents == {"first version", "second version"}


def test_import_upload_rejects_unsupported_format_without_creating_document(client: TestClient) -> None:
    response = client.post(
        "/api/documents/import",
        files={"file": ("sample.xml", b"<note>hello world</note>", "application/xml")},
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unsupported import format 'xml'"}
    assert client.get("/api/documents").json() == []


def test_import_cleanup_removes_file_when_db_insert_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(settings, "source_root", tmp_path / "data" / "source")

    db_module = import_module("app.db")
    reload(db_module)
    documents_module = import_module("app.services.documents")
    documents_module = reload(documents_module)

    upload = UploadFile(
        file=(tmp_path / "payload.txt").open("w+b"),
        filename="sample.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    upload.file.write(b"content")
    upload.file.seek(0)

    class FailingSession:
        def add(self, _document) -> None:
            return None

        def flush(self) -> None:
            raise RuntimeError("db insert failed")

        def rollback(self) -> None:
            return None

        def close(self) -> None:
            return None

    monkeypatch.setattr(db_module, "SessionLocal", lambda: FailingSession())

    with pytest.raises(RuntimeError, match="db insert failed"):
        documents_module.import_document(upload)

    assert list(settings.source_root.glob("*")) == []


def test_reset_bookmark_clears_resume_state(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    playback_session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": document_id},
    )
    assert playback_session_response.status_code == 201

    progress_response = client.patch(
        f"/api/playback/sessions/{playback_session_response.json()['id']}",
        json={"current_chunk_index": 1},
    )
    assert progress_response.status_code == 200

    reset_response = client.post(f"/api/documents/{document_id}/bookmark/reset")

    assert reset_response.status_code == 200
    payload = reset_response.json()
    assert payload["bookmark_enabled"] is True
    assert payload["is_finished"] is False
    assert payload["current_chunk_index"] is None
    assert payload["progress_percent"] == 0
    assert payload["last_opened_at"] is None

    summary_response = client.get("/api/documents/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["continue_reading"] == []


def test_disabling_bookmark_prevents_resume_from_reusing_saved_progress(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    playback_session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": document_id},
    )
    assert playback_session_response.status_code == 201

    progress_response = client.patch(
        f"/api/playback/sessions/{playback_session_response.json()['id']}",
        json={"current_chunk_index": 1},
    )
    assert progress_response.status_code == 200

    disable_response = client.patch(
        f"/api/documents/{document_id}/bookmark",
        json={"enabled": False},
    )

    assert disable_response.status_code == 200
    disable_payload = disable_response.json()
    assert disable_payload["bookmark_enabled"] is False
    assert disable_payload["current_chunk_index"] is None
    assert disable_payload["last_opened_at"] is None

    fresh_session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": document_id},
    )

    assert fresh_session_response.status_code == 201
    assert fresh_session_response.json()["current_chunk_index"] == 0


def test_mark_finished_sets_document_complete_and_hides_continue_reading(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"First sentence. Second sentence.", "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    finish_response = client.post(f"/api/documents/{document_id}/finished")

    assert finish_response.status_code == 200
    finish_payload = finish_response.json()
    assert finish_payload["is_finished"] is True
    assert finish_payload["progress_percent"] == 100
    assert finish_payload["current_chunk_index"] is None

    summary_response = client.get("/api/documents/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["continue_reading"] == []

    undo_response = client.delete(f"/api/documents/{document_id}/finished")
    assert undo_response.status_code == 200
    assert undo_response.json()["is_finished"] is False


def test_delete_document_removes_rows_and_files(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", LONG_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    playback_session_response = client.post(
        "/api/playback/sessions",
        json={"document_id": document_id},
    )
    assert playback_session_response.status_code == 201
    playback_session_id = playback_session_response.json()["id"]

    stored_file = next(user_source_root(1).glob("sample*.txt"))
    audio_cache_dirs = [
        path
        for path in (settings.cache_root / "audio").glob(f"*/*/{document_id}")
        if path.is_dir()
    ]
    assert audio_cache_dirs

    delete_response = client.delete(f"/api/documents/{document_id}")

    assert delete_response.status_code == 204
    assert client.get("/api/documents").json() == []
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.get(f"/api/playback/sessions/{playback_session_id}").status_code == 404
    assert not stored_file.exists()
    assert all(not path.exists() for path in audio_cache_dirs)


def test_delete_document_returns_404_for_non_owner(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    db_module = import_module("app.db")
    auth_service = import_module("app.services.auth")
    with db_module.session_scope() as session:
        auth_service.create_user(
            session,
            username="intruder",
            display_name="Intruder User",
            password="intruder-password-123",
        )

    with TestClient(client.app) as intruder_client:
        login_response = intruder_client.post(
            "/api/auth/login",
            json={"username": "intruder", "password": "intruder-password-123"},
        )
        assert login_response.status_code == 200

        delete_response = intruder_client.delete(f"/api/documents/{document_id}")
        assert delete_response.status_code == 404

    assert [document["id"] for document in client.get("/api/documents").json()] == [document_id]


def test_delete_document_conflicts_while_export_job_is_active(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", SHORT_SAMPLE_TEXT.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 201
    document_id = import_response.json()["id"]

    export_response = client.post(
        "/api/jobs/export",
        json={"document_id": document_id, "voice_preset_id": "default", "format": "wav"},
    )
    assert export_response.status_code == 201
    assert export_response.json()["status"] == "queued"

    delete_response = client.delete(f"/api/documents/{document_id}")

    assert delete_response.status_code == 409
    assert "export is still running" in delete_response.json()["detail"]
    assert [document["id"] for document in client.get("/api/documents").json()] == [document_id]
