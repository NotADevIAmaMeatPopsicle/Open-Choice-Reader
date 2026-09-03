from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from sqlalchemy import select

from app import db
from app.config import settings
import app.models.document as document_model
import app.models.job as job_model
import app.models.voice_preset as voice_preset_model
from app.tts.registry import normalize_clone_engine_id


SUPPORTED_EXPORT_FORMATS = {"wav"}
DEFAULT_VOICE_PRESET_ID = "default"
VOICE_OPTION_PRESET_PREFIX = "preset:"
SUPPORTED_CLONE_ENGINES = {"qwen3_clone"}
RETRYABLE_JOB_STATUSES = {"failed", "canceled"}
CANCELLABLE_JOB_STATUSES = {"queued", "processing"}
STALE_RECLAIMABLE_JOB_STATUSES = {"processing", "cancel_requested"}
STALE_JOB_FAILURE_DETAIL = (
    "Export worker stopped responding mid-job; retry to start a fresh export"
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def validate_export_request(
    *,
    voice_preset_id: str,
    format: str,
    clone_engine_id: str | None = None,
    user_id: int | None = None,
    session=None,
) -> "voice_preset_model.VoicePreset | None":
    if format not in SUPPORTED_EXPORT_FORMATS:
        raise ValueError(f"Unsupported export format '{format}'")

    voice_preset = resolve_voice_preset(
        voice_preset_id=voice_preset_id,
        user_id=user_id,
        session=session,
    )
    if clone_engine_id:
        if voice_preset is None:
            raise ValueError("Clone engine selection requires a saved voice preset")
        normalize_clone_engine_id(clone_engine_id)

    return voice_preset


def resolve_voice_preset(
    *, voice_preset_id: str, user_id: int | None = None, session=None
) -> "voice_preset_model.VoicePreset | None":
    normalized_voice_preset_id = normalize_voice_preset_id(voice_preset_id)
    if normalized_voice_preset_id == DEFAULT_VOICE_PRESET_ID:
        return None

    try:
        preset_id = int(normalized_voice_preset_id)
    except ValueError as error:
        raise ValueError(f"Unsupported voice preset '{voice_preset_id}'") from error

    if session is not None:
        return _get_voice_preset(
            session=session,
            preset_id=preset_id,
            voice_preset_id=voice_preset_id,
            user_id=user_id,
        )

    with db.session_scope() as scoped_session:
        return _get_voice_preset(
            session=scoped_session,
            preset_id=preset_id,
            voice_preset_id=voice_preset_id,
            user_id=user_id,
        )


def normalize_voice_preset_id(voice_preset_id: str) -> str:
    normalized = voice_preset_id.strip()
    if normalized.startswith(VOICE_OPTION_PRESET_PREFIX):
        return normalized.removeprefix(VOICE_OPTION_PRESET_PREFIX).strip()
    return normalized


def enqueue_export_job(
    *,
    document_id: int,
    voice_preset_id: str,
    clone_engine_id: str | None = None,
    format: str,
    split_chapters: bool = False,
    artifact_basename: str | None = None,
    user_id: int | None = None,
) -> "job_model.Job":
    normalized_format = format.lower()
    normalized_voice_preset_id = voice_preset_id.strip()
    normalized_clone_engine_id = (clone_engine_id or "").strip() or None

    with db.session_scope() as session:
        voice_preset = validate_export_request(
            voice_preset_id=normalized_voice_preset_id,
            format=normalized_format,
            clone_engine_id=normalized_clone_engine_id,
            user_id=user_id,
            session=session,
        )
        document = session.get(document_model.Document, document_id)
        if document is None or (user_id is not None and document.owner_user_id != user_id):
            raise LookupError(f"Document {document_id} was not found")

        normalized_basename = _normalize_artifact_basename(
            artifact_basename=artifact_basename,
            document_title=document.title,
        )
        job = job_model.Job(
            user_id=user_id,
            document_id=document.id,
            voice_preset_id=(
                DEFAULT_VOICE_PRESET_ID if voice_preset is None else str(voice_preset.id)
            ),
            clone_engine_id=(
                normalize_clone_engine_id(normalized_clone_engine_id)
                if voice_preset is not None and normalized_clone_engine_id
                else None
            ),
            format=normalized_format,
            status="queued",
            split_chapters=split_chapters,
            artifact_basename=normalized_basename,
            progress_percent=0,
            status_detail="Queued for export",
            artifact_manifest=None,
            failure_detail=None,
        )
        session.add(job)
        session.flush()
        session.refresh(job)

    return job


def list_jobs(*, user_id: int | None = None) -> list["job_model.Job"]:
    with db.session_scope() as session:
        statement = select(job_model.Job).order_by(job_model.Job.id)
        if user_id is not None:
            statement = statement.where(job_model.Job.user_id == user_id)
        return list(session.scalars(statement))


def get_job(job_id: int, *, user_id: int | None = None) -> "job_model.Job | None":
    with db.session_scope() as session:
        job = session.get(job_model.Job, job_id)
        if job is None:
            return None
        if user_id is not None and job.user_id != user_id:
            return None
        return job


def claim_next_queued_job() -> "job_model.Job | None":
    with db.session_scope() as session:
        job = session.scalar(
            select(job_model.Job).where(job_model.Job.status == "queued").order_by(job_model.Job.id)
        )
        if job is None:
            return None

        job.status = "processing"
        job.status_detail = "Preparing export"
        job.progress_percent = 0
        job.heartbeat_at = utcnow()
        session.flush()
        session.refresh(job)
        return job


def reclaim_stale_jobs(*, stale_after_minutes: int | None = None) -> int:
    threshold_minutes = (
        stale_after_minutes if stale_after_minutes is not None else settings.worker_stale_job_minutes
    )
    cutoff = utcnow() - timedelta(minutes=threshold_minutes)
    reclaimed = 0

    with db.session_scope() as session:
        candidate_jobs = list(
            session.scalars(
                select(job_model.Job).where(job_model.Job.status.in_(STALE_RECLAIMABLE_JOB_STATUSES))
            )
        )
        for job in candidate_jobs:
            heartbeat_at = job.heartbeat_at
            if heartbeat_at is not None and heartbeat_at.tzinfo is None:
                heartbeat_at = heartbeat_at.replace(tzinfo=timezone.utc)
            if heartbeat_at is not None and heartbeat_at >= cutoff:
                continue

            if job.status == "cancel_requested":
                job.status = "canceled"
                job.status_detail = "Canceled after the export worker stopped responding"
                job.failure_detail = None
            else:
                job.status = "failed"
                job.failure_detail = STALE_JOB_FAILURE_DETAIL
                job.status_detail = STALE_JOB_FAILURE_DETAIL
            job.artifact_path = None
            job.artifact_manifest = None
            reclaimed += 1

    return reclaimed


def cancel_job(job_id: int, *, user_id: int | None = None) -> "job_model.Job":
    with db.session_scope() as session:
        job = session.get(job_model.Job, job_id)
        if job is None or (user_id is not None and job.user_id != user_id):
            raise LookupError(f"Job {job_id} was not found")
        if job.status not in CANCELLABLE_JOB_STATUSES:
            raise ValueError(f"Job {job_id} cannot be canceled from status '{job.status}'")

        if job.status == "queued":
            job.status = "canceled"
            job.status_detail = "Canceled before processing"
        else:
            job.status = "cancel_requested"
            job.status_detail = "Cancellation requested"

        session.flush()
        session.refresh(job)
        return job


def retry_job(job_id: int, *, user_id: int | None = None) -> "job_model.Job":
    with db.session_scope() as session:
        job = session.get(job_model.Job, job_id)
        if job is None or (user_id is not None and job.user_id != user_id):
            raise LookupError(f"Job {job_id} was not found")
        if job.status not in RETRYABLE_JOB_STATUSES:
            raise ValueError(f"Job {job_id} cannot be retried from status '{job.status}'")

        voice_preset = validate_export_request(
            voice_preset_id=job.voice_preset_id,
            format=job.format,
            clone_engine_id=job.clone_engine_id,
            user_id=user_id,
            session=session,
        )
        retried_job = job_model.Job(
            user_id=user_id if user_id is not None else job.user_id,
            document_id=job.document_id,
            voice_preset_id=DEFAULT_VOICE_PRESET_ID if voice_preset is None else str(voice_preset.id),
            clone_engine_id=job.clone_engine_id,
            format=job.format,
            status="queued",
            split_chapters=job.split_chapters,
            artifact_basename=job.artifact_basename,
            progress_percent=0,
            status_detail="Queued for export",
            artifact_manifest=None,
            artifact_path=None,
            failure_detail=None,
        )
        session.add(retried_job)
        session.flush()
        session.refresh(retried_job)
        return retried_job


def can_retry_job(job: "job_model.Job") -> bool:
    return job.status in RETRYABLE_JOB_STATUSES


def can_cancel_job(job: "job_model.Job") -> bool:
    return job.status in CANCELLABLE_JOB_STATUSES


def _normalize_artifact_basename(*, artifact_basename: str | None, document_title: str) -> str:
    raw_value = (artifact_basename or "").strip() or document_title.strip() or "export"
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", raw_value).strip("-").lower()
    return normalized or "export"


def _get_voice_preset(
    *, session, preset_id: int, voice_preset_id: str, user_id: int | None = None
) -> "voice_preset_model.VoicePreset":
    voice_preset = session.get(voice_preset_model.VoicePreset, preset_id)
    if voice_preset is None or (user_id is not None and voice_preset.owner_user_id != user_id):
        raise ValueError(f"Unsupported voice preset '{voice_preset_id}'")
    if voice_preset.engine not in SUPPORTED_CLONE_ENGINES:
        raise ValueError(f"Voice preset {voice_preset.id} uses unsupported engine '{voice_preset.engine}'")

    if not voice_preset.transcript.strip():
        raise ValueError(f"Voice preset {voice_preset.id} is missing its transcript")

    reference_path = Path(voice_preset.reference_path)
    if not reference_path.is_file():
        raise ValueError(f"Voice preset {voice_preset.id} is missing its reference audio")

    return voice_preset
