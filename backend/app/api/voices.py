from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.voice import VoiceOptionRead, VoicePresetRead, VoiceTranscriptionRead
from app.services.voice_transcription import transcribe_reference_audio
from app.services.voice_preview import get_voice_preview_audio_path
from app.services.voice_presets import create_voice_preset, list_voice_presets
from app.tts.registry import list_voice_options


router = APIRouter(prefix="/api/voices", tags=["voices"])


@router.get("/presets", response_model=list[VoicePresetRead], response_model_exclude_none=True)
def list_voice_presets_route(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[VoicePresetRead]:
    return [
        VoicePresetRead.model_validate(voice_preset)
        for voice_preset in list_voice_presets(owner_user_id=current_user.id)
    ]


@router.get("/options", response_model=list[VoiceOptionRead])
def list_voice_options_route(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[VoiceOptionRead]:
    return [
        VoiceOptionRead.model_validate(voice_option)
        for voice_option in list_voice_options(user_id=current_user.id)
    ]


@router.get("/preview")
def preview_voice_route(
    voice_option_id: str = Query(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    try:
        audio_path = get_voice_preview_audio_path(
            voice_option_id=voice_option_id,
            user_id=current_user.id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return FileResponse(audio_path, media_type="audio/wav")


@router.post("/presets", response_model=VoicePresetRead, status_code=201, response_model_exclude_none=True)
def create_voice_preset_route(
    name: Annotated[str, Form(min_length=1, max_length=300)],
    transcript: Annotated[str, Form(min_length=1, max_length=100_000)],
    reference_audio: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> VoicePresetRead:
    try:
        voice_preset = create_voice_preset(
            name=name,
            reference_audio=reference_audio,
            transcript=transcript,
            owner_user_id=current_user.id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return VoicePresetRead.model_validate(voice_preset)


@router.post("/transcribe-reference", response_model=VoiceTranscriptionRead)
def transcribe_reference_audio_route(
    reference_audio: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> VoiceTranscriptionRead:
    del current_user
    try:
        result = transcribe_reference_audio(reference_audio=reference_audio)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return VoiceTranscriptionRead.model_validate(result)
