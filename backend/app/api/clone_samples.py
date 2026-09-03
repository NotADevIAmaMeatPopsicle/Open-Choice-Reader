import io

from fastapi import APIRouter, Depends, HTTPException
from starlette.datastructures import Headers, UploadFile

from app.api.dependencies import CurrentUser, get_current_user
from app.config import settings
from app.schemas.clone_sample import CloneSampleImportRequest, CloneSampleSearchRead
from app.schemas.voice import VoicePresetRead
from app.services.clone_sample_sources import search_clone_sample_candidates
from app.services.remote_fetch import fetch_remote_resource
from app.services.voice_presets import create_voice_preset


router = APIRouter(prefix="/api/clone-samples", tags=["clone-samples"])


@router.get("/search", response_model=CloneSampleSearchRead)
def search_clone_samples_route(
    q: str,
    limit: int = 10,
    current_user: CurrentUser = Depends(get_current_user),
) -> CloneSampleSearchRead:
    del current_user
    candidates = search_clone_sample_candidates(q, limit=limit)
    return CloneSampleSearchRead.model_validate({"query": q, "items": candidates})


@router.post("/import", response_model=VoicePresetRead, status_code=201, response_model_exclude_none=True)
def import_clone_sample_route(
    payload: CloneSampleImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> VoicePresetRead:
    if not payload.transcript.strip():
        raise HTTPException(status_code=422, detail="transcript is required")

    try:
        resource = fetch_remote_resource(
            payload.audio_url,
            max_bytes=settings.remote_audio_max_bytes,
            timeout_seconds=20,
            user_agent="OpenChoiceReader/0.1 (+voice-sample)",
        )
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=422, detail=f"Unable to download reference audio: {error}") from error

    upload = UploadFile(
        file=io.BytesIO(resource.body),
        filename=f"{payload.provider}-reference.mp3",
        headers=Headers({"content-type": resource.content_type or "audio/mpeg"}),
    )
    try:
        preset = create_voice_preset(
            name=payload.title,
            reference_audio=upload,
            transcript=payload.transcript,
            owner_user_id=current_user.id,
            source_provider=payload.provider,
            source_url=payload.source_url,
            transcript_source_url=payload.transcript_source_url,
            license_label=payload.license_label,
            provenance_note=payload.provenance_note,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return VoicePresetRead.model_validate(preset)
