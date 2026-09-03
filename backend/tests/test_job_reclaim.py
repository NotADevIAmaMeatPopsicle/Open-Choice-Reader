from datetime import timedelta
from importlib import import_module, reload
from pathlib import Path

import pytest
from starlette.datastructures import Headers, UploadFile

from app import db
from app.config import settings
from app.models.job import Job

SAMPLE_TEXT = "First sentence. Second sentence."


def _load_modules():
    models_module = import_module("app.models")
    reload(models_module)
    reload(import_module("app.models.document"))
    reload(import_module("app.models.document_profile"))
    reload(import_module("app.models.document_progress"))
    reload(import_module("app.models.job"))
    reload(import_module("app.models.section"))
    reload(import_module("app.models.text_chunk"))
    reload(import_module("app.models.voice_preset"))

    db_module = import_module("app.db")
    reload(db_module)

    documents_module = reload(import_module("app.services.documents"))
    jobs_module = reload(import_module("app.services.jobs"))
    reload(import_module("app.services.audio_cache"))
    reload(import_module("app.tts.mock_engine"))
    reload(import_module("app.tts.registry"))
    worker_jobs_module = reload(import_module("app.worker.jobs"))
    worker_runner_module = reload(import_module("app.worker.runner"))

    return {
        "documents": documents_module,
        "jobs": jobs_module,
        "worker_jobs": worker_jobs_module,
        "worker_runner": worker_runner_module,
    }


def _upload_file(tmp_path: Path, *, filename: str, content: bytes) -> UploadFile:
    upload = UploadFile(
        file=(tmp_path / filename).open("w+b"),
        filename=filename,
        headers=Headers({"content-type": "text/plain"}),
    )
    upload.file.write(content)
    upload.file.seek(0)
    return upload


def _import_document(modules, tmp_path: Path):
    upload = _upload_file(tmp_path, filename="sample.txt", content=SAMPLE_TEXT.encode("utf-8"))
    try:
        return modules["documents"].import_document(upload)
    finally:
        upload.file.close()


def _claim_processing_job(modules, tmp_path: Path) -> int:
    document = _import_document(modules, tmp_path)
    modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id="default",
        format="wav",
    )
    claimed_job = modules["jobs"].claim_next_queued_job()
    assert claimed_job is not None
    return claimed_job.id


def _set_job_heartbeat(modules, job_id: int, *, minutes_ago: int | None) -> None:
    with db.session_scope() as session:
        job = session.get(Job, job_id)
        assert job is not None
        if minutes_ago is None:
            job.heartbeat_at = None
        else:
            job.heartbeat_at = modules["jobs"].utcnow() - timedelta(minutes=minutes_ago)


def _get_job(job_id: int) -> Job:
    with db.session_scope() as session:
        job = session.get(Job, job_id)
        assert job is not None
        session.refresh(job)
        return job


def test_claiming_a_job_records_a_worker_heartbeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    job_id = _claim_processing_job(modules, tmp_path)

    job = _get_job(job_id)
    assert job.status == "processing"
    assert job.heartbeat_at is not None


def test_reclaim_marks_stale_processing_jobs_failed_and_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    job_id = _claim_processing_job(modules, tmp_path)
    _set_job_heartbeat(modules, job_id, minutes_ago=30)

    assert modules["jobs"].reclaim_stale_jobs() == 1

    job = _get_job(job_id)
    assert job.status == "failed"
    assert job.failure_detail == modules["jobs"].STALE_JOB_FAILURE_DETAIL
    assert job.artifact_path is None
    assert modules["jobs"].can_retry_job(job) is True


def test_reclaim_leaves_recent_processing_jobs_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    job_id = _claim_processing_job(modules, tmp_path)

    assert modules["jobs"].reclaim_stale_jobs() == 0

    job = _get_job(job_id)
    assert job.status == "processing"
    assert job.failure_detail is None


def test_reclaim_cancels_stale_cancel_requested_jobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    job_id = _claim_processing_job(modules, tmp_path)
    modules["jobs"].cancel_job(job_id)
    _set_job_heartbeat(modules, job_id, minutes_ago=30)

    assert modules["jobs"].reclaim_stale_jobs() == 1

    job = _get_job(job_id)
    assert job.status == "canceled"
    assert job.failure_detail is None


def test_reclaim_fails_legacy_processing_jobs_without_heartbeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    job_id = _claim_processing_job(modules, tmp_path)
    _set_job_heartbeat(modules, job_id, minutes_ago=None)

    assert modules["jobs"].reclaim_stale_jobs() == 1

    job = _get_job(job_id)
    assert job.status == "failed"
    assert job.failure_detail == modules["jobs"].STALE_JOB_FAILURE_DETAIL


def test_run_once_reclaims_stale_jobs_before_claiming_new_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'test.db'}")
    modules = _load_modules()
    modules["documents"].init_database()

    stale_job_id = _claim_processing_job(modules, tmp_path)
    _set_job_heartbeat(modules, stale_job_id, minutes_ago=30)

    document = _import_document(modules, tmp_path)
    queued_job = modules["jobs"].enqueue_export_job(
        document_id=document.id,
        voice_preset_id="default",
        format="wav",
    )

    processed_job_ids: list[int] = []
    monkeypatch.setattr(
        modules["worker_runner"],
        "process_export_job",
        lambda job: processed_job_ids.append(job.id),
    )

    assert modules["worker_runner"].run_once() == 1

    assert processed_job_ids == [queued_job.id]
    stale_job = _get_job(stale_job_id)
    assert stale_job.status == "failed"
    assert stale_job.failure_detail == modules["jobs"].STALE_JOB_FAILURE_DETAIL
