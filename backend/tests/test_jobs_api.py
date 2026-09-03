from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.models.job import Job
from app.models.voice_preset import VoicePreset


def _load_app():
    models_module = import_module("app.models")
    reload(models_module)
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
    reload(import_module("app.services.jobs"))
    reload(import_module("app.services.voice_presets"))
    reload(import_module("app.api.documents"))
    reload(import_module("app.api.jobs"))
    reload(import_module("app.api.voices"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_export_job_request_returns_queued_status(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document_id"] == 1
    assert payload["voice_preset_id"] == "default"
    assert payload["format"] == "wav"
    assert payload["status"] == "queued"
    assert payload["split_chapters"] is False
    assert payload["artifact_basename"] == "sample"
    assert payload["progress_percent"] == 0
    assert payload["status_detail"] == "Queued for export"
    assert payload["download_url"] is None
    assert payload["failure_detail"] is None
    assert payload["artifacts"] == []
    assert payload["can_cancel"] is True
    assert payload["can_retry"] is False


def test_export_job_request_rejects_missing_document(client: TestClient) -> None:
    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": 999,
            "voice_preset_id": "default",
            "format": "wav",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Document 999 was not found"}


def test_export_job_request_rejects_unsupported_format_without_queueing(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "mp3",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unsupported export format 'mp3'"}
    assert client.get("/api/jobs").json() == []


def test_export_job_request_rejects_unsupported_voice_without_queueing(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "clone-voice",
            "format": "wav",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unsupported voice preset 'clone-voice'"}
    assert client.get("/api/jobs").json() == []


def test_export_job_request_accepts_saved_voice_preset(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    preset_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert preset_response.status_code == 201

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": str(preset_response.json()["id"]),
            "format": "wav",
            "clone_engine_id": "qwen3_clone_1_7b",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == response.json()["id"]
    assert payload["document_id"] == import_response.json()["id"]
    assert payload["voice_preset_id"] == str(preset_response.json()["id"])
    assert payload["clone_engine_id"] == "qwen3_clone_1_7b"
    assert payload["format"] == "wav"
    assert payload["status"] == "queued"
    assert payload["split_chapters"] is False
    assert payload["download_url"] is None
    assert payload["failure_detail"] is None
    assert payload["artifacts"] == []


def test_export_job_request_accepts_prefixed_voice_preset_id(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    preset_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert preset_response.status_code == 201

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": f"preset:{preset_response.json()['id']}",
            "format": "wav",
        },
    )

    assert response.status_code == 201
    assert response.json()["voice_preset_id"] == str(preset_response.json()["id"])


def test_export_job_request_rejects_unknown_clone_engine_id(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    preset_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert preset_response.status_code == 201

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": str(preset_response.json()["id"]),
            "clone_engine_id": "qwen3_clone_9_9b",
            "format": "wav",
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Unsupported clone engine 'qwen3_clone_9_9b'"}


def test_export_job_request_rejects_saved_voice_preset_with_missing_reference_audio(
    client: TestClient,
) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    preset_response = client.post(
        "/api/voices/presets",
        data={"name": "Narrator", "transcript": "Alice reads sample text."},
        files={"reference_audio": ("narrator.wav", b"RIFFdemo", "audio/wav")},
    )
    assert preset_response.status_code == 201

    with db.session_scope() as session:
        voice_preset = session.get(VoicePreset, preset_response.json()["id"])
        assert voice_preset is not None
        Path(voice_preset.reference_path).unlink()

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": str(preset_response.json()["id"]),
            "format": "wav",
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": f"Voice preset {preset_response.json()['id']} is missing its reference audio"
    }
    assert client.get("/api/jobs").json() == []


def test_jobs_listing_returns_result_metadata_for_completed_and_failed_jobs(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    completed_job = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
        },
    )
    failed_job = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
        },
    )
    assert completed_job.status_code == 201
    assert failed_job.status_code == 201

    artifact_path = Path(settings.export_root) / f"job-{completed_job.json()['id']}.wav"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"RIFFfixture")

    with db.session_scope() as session:
        stored_completed = session.get(Job, completed_job.json()["id"])
        stored_failed = session.get(Job, failed_job.json()["id"])
        assert stored_completed is not None
        assert stored_failed is not None
        stored_completed.status = "completed"
        stored_completed.artifact_path = str(artifact_path)
        stored_completed.failure_detail = None
        stored_failed.status = "failed"
        stored_failed.artifact_path = None
        stored_failed.failure_detail = "piper synthesis failed"

    response = client.get("/api/jobs")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == completed_job.json()["id"]
    assert payload[0]["status"] == "completed"
    assert payload[0]["download_url"] == f"/api/jobs/{completed_job.json()['id']}/download"
    assert payload[0]["progress_percent"] == 100
    assert payload[0]["artifacts"] == [
        {
            "artifact_id": "0",
            "download_url": f"/api/jobs/{completed_job.json()['id']}/download",
            "filename": artifact_path.name,
            "label": "Merged audiobook",
            "section_title": None,
        }
    ]
    assert payload[1]["id"] == failed_job.json()["id"]
    assert payload[1]["status"] == "failed"
    assert payload[1]["download_url"] is None
    assert payload[1]["failure_detail"] == "piper synthesis failed"
    assert payload[1]["can_retry"] is True


def test_job_detail_and_download_surface_completed_exports(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    create_response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
        },
    )
    assert create_response.status_code == 201

    artifact_path = Path(settings.export_root) / f"job-{create_response.json()['id']}.wav"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"RIFFfixture")

    with db.session_scope() as session:
        stored_job = session.get(Job, create_response.json()["id"])
        assert stored_job is not None
        stored_job.status = "completed"
        stored_job.artifact_path = str(artifact_path)

    detail_response = client.get(f"/api/jobs/{create_response.json()['id']}")

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == create_response.json()["id"]
    assert detail_payload["document_id"] == import_response.json()["id"]
    assert detail_payload["voice_preset_id"] == "default"
    assert detail_payload["format"] == "wav"
    assert detail_payload["status"] == "completed"
    assert detail_payload["download_url"] == f"/api/jobs/{create_response.json()['id']}/download"
    assert detail_payload["failure_detail"] is None
    assert detail_payload["artifacts"] == [
        {
            "artifact_id": "0",
            "download_url": f"/api/jobs/{create_response.json()['id']}/download",
            "filename": artifact_path.name,
            "label": "Merged audiobook",
            "section_title": None,
        }
    ]

    download_response = client.get(detail_payload["download_url"])

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "audio/wav"
    assert download_response.content == b"RIFFfixture"


def test_export_job_request_accepts_split_chapters_and_artifact_name(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
            "split_chapters": True,
            "artifact_basename": "Alice Nightly",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["split_chapters"] is True
    assert payload["artifact_basename"] == "alice-nightly"
    assert payload["status_detail"] == "Queued for export"


def test_cancel_job_route_marks_a_queued_job_as_canceled(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    create_response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
        },
    )
    assert create_response.status_code == 201

    cancel_response = client.post(f"/api/jobs/{create_response.json()['id']}/cancel")

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "canceled"
    assert cancel_response.json()["can_retry"] is True
    assert cancel_response.json()["can_cancel"] is False


def test_retry_job_route_clones_a_failed_job_into_a_new_attempt(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    create_response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
            "split_chapters": True,
            "artifact_basename": "Alice Retry",
        },
    )
    assert create_response.status_code == 201

    with db.session_scope() as session:
        stored_job = session.get(Job, create_response.json()["id"])
        assert stored_job is not None
        stored_job.status = "failed"
        stored_job.failure_detail = "worker crashed"

    retry_response = client.post(f"/api/jobs/{create_response.json()['id']}/retry")

    assert retry_response.status_code == 201
    payload = retry_response.json()
    assert payload["id"] != create_response.json()["id"]
    assert payload["document_id"] == import_response.json()["id"]
    assert payload["split_chapters"] is True
    assert payload["artifact_basename"] == "alice-retry"
    assert payload["status"] == "queued"
    assert payload["can_cancel"] is True


def test_jobs_listing_surfaces_split_artifact_library_metadata(client: TestClient) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    create_response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
            "split_chapters": True,
            "artifact_basename": "Alice Split",
        },
    )
    assert create_response.status_code == 201

    export_root = Path(settings.export_root)
    export_root.mkdir(parents=True, exist_ok=True)
    artifact_one = export_root / "alice-split-01-chapter-one.wav"
    artifact_two = export_root / "alice-split-02-chapter-two.wav"
    artifact_one.write_bytes(b"RIFFone")
    artifact_two.write_bytes(b"RIFFtwo")

    with db.session_scope() as session:
        stored_job = session.get(Job, create_response.json()["id"])
        assert stored_job is not None
        stored_job.status = "completed"
        stored_job.artifact_path = None
        stored_job.failure_detail = None
        stored_job.progress_percent = 100
        stored_job.artifact_manifest = (
            '[{"filename":"alice-split-01-chapter-one.wav","label":"Chapter 1","section_title":"Chapter One","path":"'
            + str(artifact_one).replace("\\", "\\\\")
            + '"},{"filename":"alice-split-02-chapter-two.wav","label":"Chapter 2","section_title":"Chapter Two","path":"'
            + str(artifact_two).replace("\\", "\\\\")
            + '"}]'
        )

    response = client.get("/api/jobs")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["download_url"] is None
    assert payload["artifacts"] == [
        {
            "artifact_id": "0",
            "download_url": f"/api/jobs/{create_response.json()['id']}/artifacts/0/download",
            "filename": "alice-split-01-chapter-one.wav",
            "label": "Chapter 1",
            "section_title": "Chapter One",
        },
        {
            "artifact_id": "1",
            "download_url": f"/api/jobs/{create_response.json()['id']}/artifacts/1/download",
            "filename": "alice-split-02-chapter-two.wav",
            "label": "Chapter 2",
            "section_title": "Chapter Two",
        },
    ]
