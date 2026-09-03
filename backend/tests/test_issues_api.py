from importlib import import_module, reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.models.job import Job
from app.services.user_storage import user_source_root
from app.tts.base import EngineStatus


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
    reload(import_module("app.services.issues"))
    reload(import_module("app.api.issues"))

    main_module = import_module("app.main")
    return reload(main_module).app


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")

    app = _load_app()

    with TestClient(app) as test_client:
        yield test_client


def test_issues_api_aggregates_export_failures_missing_sources_and_engine_warnings(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import_response = client.post(
        "/api/documents/import",
        files={"file": ("sample.txt", b"hello world", "text/plain")},
    )
    assert import_response.status_code == 201

    create_job_response = client.post(
        "/api/jobs/export",
        json={
            "document_id": import_response.json()["id"],
            "voice_preset_id": "default",
            "format": "wav",
        },
    )
    assert create_job_response.status_code == 201

    stored_file = next(user_source_root(1).glob("sample*"))
    stored_file.unlink()

    with db.session_scope() as session:
        job = session.get(Job, create_job_response.json()["id"])
        assert job is not None
        job.status = "failed"
        job.failure_detail = "Piper binary missing"

    issues_module = import_module("app.services.issues")
    monkeypatch.setattr(
        issues_module,
        "list_engine_statuses",
        lambda: [
            EngineStatus(
                engine="piper",
                display_name="Fast reader",
                availability="unavailable",
                availability_detail="Piper binary missing",
                supports_live_reading=True,
                supports_export=True,
            )
        ],
    )

    response = client.get("/api/issues")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 3
    assert payload["counts_by_severity"] == {"error": 2, "warning": 1}
    assert [issue["issue_type"] for issue in payload["items"]] == [
        "missing_source",
        "export_failure",
        "engine_warning",
    ]
