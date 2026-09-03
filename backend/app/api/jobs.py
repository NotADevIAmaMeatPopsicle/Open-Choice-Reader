from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.job import JobExportCreate, JobRead
from app.services.artifacts import resolve_job_artifact_path, serialize_job_artifacts
from app.services.jobs import (
    can_cancel_job,
    can_retry_job,
    cancel_job,
    enqueue_export_job,
    get_job,
    list_jobs,
    retry_job,
)


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs_route(current_user: CurrentUser = Depends(get_current_user)) -> list[JobRead]:
    return [_serialize_job(job) for job in list_jobs(user_id=current_user.id)]


@router.get("/{job_id}", response_model=JobRead)
def get_job_route(job_id: int, current_user: CurrentUser = Depends(get_current_user)) -> JobRead:
    job = get_job(job_id, user_id=current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found")
    return _serialize_job(job)


@router.get("/{job_id}/download")
def download_job_route(job_id: int, current_user: CurrentUser = Depends(get_current_user)) -> FileResponse:
    job = get_job(job_id, user_id=current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found")
    if job.status != "completed" or not job.artifact_path:
        raise HTTPException(status_code=409, detail=f"Job {job_id} is not ready for download")

    artifact_path = Path(job.artifact_path)
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail=f"Export artifact for job {job_id} is missing")

    return FileResponse(
        path=artifact_path,
        media_type="audio/wav",
        filename=artifact_path.name,
    )


@router.get("/{job_id}/artifacts/{artifact_index}/download")
def download_job_artifact_route(
    job_id: int,
    artifact_index: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    job = get_job(job_id, user_id=current_user.id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} was not found")

    try:
        artifact_path = resolve_job_artifact_path(job=job, artifact_index=artifact_index)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    if not artifact_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {artifact_index} for job {job_id} is missing",
        )

    return FileResponse(
        path=artifact_path,
        media_type="audio/wav",
        filename=artifact_path.name,
    )


@router.post("/export", response_model=JobRead, status_code=201)
def create_export_job(
    payload: JobExportCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> JobRead:
    try:
        job = enqueue_export_job(
            document_id=payload.document_id,
            voice_preset_id=payload.voice_preset_id,
            clone_engine_id=payload.clone_engine_id,
            format=payload.format,
            split_chapters=payload.split_chapters,
            artifact_basename=payload.artifact_basename,
            user_id=current_user.id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return _serialize_job(job)


@router.post("/{job_id}/cancel", response_model=JobRead)
def cancel_job_route(job_id: int, current_user: CurrentUser = Depends(get_current_user)) -> JobRead:
    try:
        job = cancel_job(job_id, user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _serialize_job(job)


@router.post("/{job_id}/retry", response_model=JobRead, status_code=201)
def retry_job_route(job_id: int, current_user: CurrentUser = Depends(get_current_user)) -> JobRead:
    try:
        job = retry_job(job_id, user_id=current_user.id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return _serialize_job(job)


def _serialize_job(job) -> JobRead:
    return JobRead.model_validate(
        {
            "id": job.id,
            "document_id": job.document_id,
            "voice_preset_id": job.voice_preset_id,
            "clone_engine_id": job.clone_engine_id,
            "format": job.format,
            "status": job.status,
            "split_chapters": job.split_chapters,
            "artifact_basename": job.artifact_basename,
            "progress_percent": _build_progress_percent(job),
            "status_detail": job.status_detail,
            "download_url": _build_download_url(job),
            "failure_detail": job.failure_detail,
            "artifacts": serialize_job_artifacts(job),
            "can_retry": can_retry_job(job),
            "can_cancel": can_cancel_job(job),
        }
    )


def _build_download_url(job) -> str | None:
    if job.status != "completed" or not job.artifact_path:
        return None
    return f"/api/jobs/{job.id}/download"


def _build_progress_percent(job) -> int:
    if job.status == "completed":
        return 100
    return job.progress_percent
