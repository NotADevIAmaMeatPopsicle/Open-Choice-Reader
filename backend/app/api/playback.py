from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.playback import PlaybackPrebufferRead, PlaybackSessionCreate, PlaybackSessionRead, PlaybackSessionUpdate
from app.services.playback import (
    PlaybackSynthesisError,
    create_playback_session,
    get_playback_session_state,
    get_playback_audio_path,
    prebuffer_playback_session,
    update_playback_session,
)


router = APIRouter(prefix="/api/playback", tags=["playback"])


@router.post("/sessions", response_model=PlaybackSessionRead, status_code=201)
def create_playback_session_route(
    payload: PlaybackSessionCreate,
    current_user: CurrentUser = Depends(get_current_user),
) -> PlaybackSessionRead:
    try:
        playback_session = create_playback_session(
            document_id=payload.document_id,
            start_section_id=payload.start_section_id,
            playback_speed=payload.playback_speed,
            voice_option_id=payload.voice_option_id,
            user_id=current_user.id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PlaybackSynthesisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return PlaybackSessionRead.model_validate(playback_session)


@router.get("/audio/{session_id}")
def get_playback_audio_route(
    session_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    try:
        audio_path = get_playback_audio_path(session_id=session_id, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(audio_path, media_type="audio/wav")


@router.get("/sessions/{session_id}", response_model=PlaybackSessionRead)
def get_playback_session_route(
    session_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> PlaybackSessionRead:
    try:
        playback_session = get_playback_session_state(session_id=session_id, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return PlaybackSessionRead.model_validate(playback_session)


@router.post("/sessions/{session_id}/prebuffer", response_model=PlaybackPrebufferRead)
def prebuffer_playback_session_route(
    session_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> PlaybackPrebufferRead:
    try:
        prebuffer_result = prebuffer_playback_session(session_id=session_id, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PlaybackSynthesisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return PlaybackPrebufferRead.model_validate(prebuffer_result)


@router.patch("/sessions/{session_id}", response_model=PlaybackSessionRead)
def update_playback_session_route(
    session_id: int,
    payload: PlaybackSessionUpdate,
    current_user: CurrentUser = Depends(get_current_user),
) -> PlaybackSessionRead:
    try:
        playback_session = update_playback_session(
            session_id=session_id,
            current_chunk_index=payload.current_chunk_index,
            playback_speed=payload.playback_speed,
            voice_option_id=payload.voice_option_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IndexError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PlaybackSynthesisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return PlaybackSessionRead.model_validate(playback_session)
