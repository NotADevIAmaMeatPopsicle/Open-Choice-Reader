from dataclasses import dataclass
from pathlib import Path
import subprocess

from sqlalchemy import desc, func, select

from app import db
from app.config import settings
from app.models.document import Document
from app.models.document_profile import DocumentProfile
from app.models.playback_session import PlaybackSession
from app.models.section import Section
from app.models.text_chunk import TextChunk
from app.services.audio_cache import build_chunk_audio_cache_path, populate_cached_audio
from app.services.cache_eviction import touch_cached_audio
from app.services.user_storage import user_cache_root
from app.services.library_view import get_resume_chunk_index, upsert_document_progress
from app.services.settings import (
    DEFAULT_NARRATION_PACE,
    get_default_playback_speed,
    get_live_narration_pace,
    get_voice_settings,
)
from app.tts.registry import build_live_engine_for_voice_option, resolve_voice_option


@dataclass
class PlaybackSectionChunkRecord:
    chunk_index: int
    text: str
    is_current: bool


@dataclass
class PlaybackSessionResult:
    id: int
    document_id: int
    document_title: str
    document_author: str | None
    cover_url: str
    current_chunk_index: int
    total_chunks: int
    audio_url: str
    engine_name: str
    voice_option_id: str | None
    voice_model_name: str | None
    playback_speed: float
    current_chunk_text: str
    current_section_title: str | None
    section_chunks: list[PlaybackSectionChunkRecord]


@dataclass
class PlaybackPrebufferResult:
    session_id: int
    target_chunk_index: int | None
    status: str
    audio_url: str | None
    detail: str | None = None


class PlaybackSynthesisError(RuntimeError):
    """Raised when a configured voice cannot generate playback audio."""


def _get_document_chunk(*, session, document_id: int, chunk_index: int) -> TextChunk | None:
    return session.scalar(
        select(TextChunk)
        .join(Section, TextChunk.section_id == Section.id)
        .where(Section.document_id == document_id)
        .order_by(Section.position, TextChunk.position)
        .offset(chunk_index)
        .limit(1)
    )


def _get_section_start_chunk(*, session, document_id: int, section_id: int) -> tuple[TextChunk, int]:
    section = session.get(Section, section_id)
    if section is None or section.document_id != document_id:
        raise LookupError(f"Section {section_id} was not found for document {document_id}")

    chunk = session.scalar(
        select(TextChunk)
        .where(TextChunk.section_id == section.id)
        .order_by(TextChunk.position)
        .limit(1)
    )
    if chunk is None:
        raise ValueError(f"Section {section_id} has no text chunks")

    chunk_start_index = session.scalar(
        select(func.count(TextChunk.id))
        .join(Section, TextChunk.section_id == Section.id)
        .where(Section.document_id == document_id, Section.position < section.position)
    )
    return chunk, int(chunk_start_index or 0)


def _resolve_live_voice_option_id(
    requested_voice_option_id: str | None,
    *,
    user_id: int | None = None,
) -> str:
    candidate_voice_option_id = (requested_voice_option_id or "").strip()
    if not candidate_voice_option_id:
        candidate_voice_option_id = get_voice_settings(user_id=user_id).default_live_voice_id

    voice_option = resolve_voice_option(candidate_voice_option_id, user_id=user_id)
    if voice_option is None:
        raise ValueError(f"Unknown live-reading voice '{candidate_voice_option_id}'")
    if not voice_option.supports_live_reading:
        raise ValueError(f"Voice '{candidate_voice_option_id}' does not support live reading")
    if settings.tts_engine != "mock" and voice_option.availability != "available":
        raise ValueError(
            f"Voice '{candidate_voice_option_id}' is unavailable. "
            f"{voice_option.availability_detail}"
        )

    return candidate_voice_option_id


def _get_chunk_audio_path(
    *,
    document_id: int,
    chunk: TextChunk,
    voice_option_id: str,
    user_id: int | None = None,
) -> tuple[str, Path, str | None]:
    is_preset_voice = voice_option_id.startswith("preset:")
    narration_pace = (
        DEFAULT_NARRATION_PACE if is_preset_voice else get_live_narration_pace(user_id=user_id)
    )
    engine = build_live_engine_for_voice_option(voice_option_id, user_id=user_id, pace=narration_pace)
    voice_cache_key = (
        voice_option_id
        if is_preset_voice or narration_pace == DEFAULT_NARRATION_PACE
        else f"{voice_option_id}|pace-{narration_pace:.2f}"
    )
    audio_path = build_chunk_audio_cache_path(
        engine_name=engine.name,
        document_id=document_id,
        chunk_id=chunk.id,
        text=chunk.text,
        voice_cache_key=voice_cache_key,
    )
    try:
        populate_cached_audio(engine=engine, text=chunk.text, output_path=audio_path)
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        raise PlaybackSynthesisError(
            "The selected text-to-speech voice could not generate audio on this server."
        ) from exc
    return engine.name, audio_path, getattr(engine, "model_name", None)


def _find_latest_document_session(
    *,
    session,
    document_id: int,
    user_id: int | None = None,
) -> PlaybackSession | None:
    statement = select(PlaybackSession).where(PlaybackSession.document_id == document_id)
    if user_id is not None:
        statement = statement.where(PlaybackSession.user_id == user_id)
    return session.scalar(
        statement.order_by(desc(PlaybackSession.id)).limit(1)
    )


def _build_playback_session_result(*, session, playback_session: PlaybackSession) -> PlaybackSessionResult:
    document = session.get(Document, playback_session.document_id)
    if document is None:
        raise ValueError(f"Document {playback_session.document_id} was not found")

    profile = session.get(DocumentProfile, playback_session.document_id)
    total_chunks = profile.total_chunks if profile is not None else 0
    document_author = profile.author if profile is not None else None

    current_chunk = session.get(TextChunk, playback_session.chunk_id)
    if current_chunk is None:
        raise ValueError(f"Chunk {playback_session.chunk_id} was not found for playback session {playback_session.id}")

    current_section = session.get(Section, current_chunk.section_id)
    if current_section is None:
        raise ValueError(f"Section for playback session {playback_session.id} was not found")

    section_start_index = session.scalar(
        select(func.count(TextChunk.id))
        .join(Section, TextChunk.section_id == Section.id)
        .where(
            Section.document_id == playback_session.document_id,
            Section.position < current_section.position,
        )
    )
    absolute_section_start = int(section_start_index or 0)
    section_chunks = list(
        session.scalars(
            select(TextChunk)
            .where(TextChunk.section_id == current_section.id)
            .order_by(TextChunk.position)
        )
    )
    resolved_voice_option = resolve_voice_option(
        playback_session.voice_option_id or "",
        user_id=playback_session.user_id,
    )

    return PlaybackSessionResult(
        id=playback_session.id,
        document_id=playback_session.document_id,
        document_title=document.title,
        document_author=document_author,
        cover_url=f"/api/documents/{document.id}/cover",
        current_chunk_index=playback_session.current_chunk_index,
        total_chunks=total_chunks,
        audio_url=f"/api/playback/audio/{playback_session.id}",
        engine_name=playback_session.engine_name,
        voice_option_id=playback_session.voice_option_id,
        voice_model_name=resolved_voice_option.model_name if resolved_voice_option is not None else None,
        playback_speed=round(playback_session.playback_speed or 1.0, 2),
        current_chunk_text=current_chunk.text,
        current_section_title=current_section.title,
        section_chunks=[
            PlaybackSectionChunkRecord(
                chunk_index=absolute_section_start + chunk.position,
                text=chunk.text,
                is_current=chunk.id == current_chunk.id,
            )
            for chunk in section_chunks
        ],
    )


def create_playback_session(
    *,
    document_id: int,
    start_section_id: int | None = None,
    playback_speed: float | None = None,
    voice_option_id: str | None = None,
    user_id: int | None = None,
) -> PlaybackSessionResult:
    with db.session_scope() as session:
        document = session.get(Document, document_id)
        if document is None or (user_id is not None and document.owner_user_id != user_id):
            raise LookupError(f"Document {document_id} was not found")

        selected_voice_option_id = _resolve_live_voice_option_id(voice_option_id, user_id=user_id)
        resume_chunk_index = (
            get_resume_chunk_index(session=session, document_id=document_id)
            if start_section_id is None
            else None
        )

        if start_section_id is not None:
            chunk, current_chunk_index = _get_section_start_chunk(
                session=session,
                document_id=document_id,
                section_id=start_section_id,
            )
        else:
            current_chunk_index = resume_chunk_index if resume_chunk_index is not None else 0
            chunk = _get_document_chunk(
                session=session,
                document_id=document_id,
                chunk_index=current_chunk_index,
            )
            if chunk is None:
                raise ValueError(f"Document {document_id} has no text chunks")

            if voice_option_id is None:
                existing_session = _find_latest_document_session(
                    session=session,
                    document_id=document_id,
                    user_id=user_id,
                )
                if (
                    existing_session is not None
                    and existing_session.current_chunk_index == current_chunk_index
                    and (existing_session.voice_option_id or selected_voice_option_id) == selected_voice_option_id
                ):
                    return _build_playback_session_result(session=session, playback_session=existing_session)

        engine_name, audio_path, _voice_model_name = _get_chunk_audio_path(
            document_id=document_id,
            chunk=chunk,
            voice_option_id=selected_voice_option_id,
            user_id=user_id,
        )

        playback_session = PlaybackSession(
            user_id=user_id,
            document_id=document_id,
            chunk_id=chunk.id,
            current_chunk_index=current_chunk_index,
            engine_name=engine_name,
            voice_option_id=selected_voice_option_id,
            playback_speed=playback_speed if playback_speed is not None else get_default_playback_speed(user_id=user_id),
            audio_path=str(audio_path),
        )
        session.add(playback_session)
        session.flush()
        upsert_document_progress(
            session=session,
            document_id=document_id,
            current_chunk_index=current_chunk_index,
        )

        return _build_playback_session_result(session=session, playback_session=playback_session)


def get_playback_session_state(*, session_id: int, user_id: int | None = None) -> PlaybackSessionResult:
    with db.session_scope() as session:
        playback_session = session.get(PlaybackSession, session_id)
        if playback_session is None or (user_id is not None and playback_session.user_id != user_id):
            raise LookupError(f"Playback session {session_id} was not found")

        return _build_playback_session_result(session=session, playback_session=playback_session)


def update_playback_session(
    *,
    session_id: int,
    current_chunk_index: int | None = None,
    playback_speed: float | None = None,
    voice_option_id: str | None = None,
    user_id: int | None = None,
) -> PlaybackSessionResult:
    with db.session_scope() as session:
        playback_session = session.get(PlaybackSession, session_id)
        if playback_session is None or (user_id is not None and playback_session.user_id != user_id):
            raise LookupError(f"Playback session {session_id} was not found")

        selected_voice_option_id = playback_session.voice_option_id or get_voice_settings(
            user_id=playback_session.user_id if user_id is None else user_id
        ).default_live_voice_id
        if voice_option_id is not None:
            selected_voice_option_id = _resolve_live_voice_option_id(
                voice_option_id,
                user_id=playback_session.user_id if user_id is None else user_id,
            )
            playback_session.voice_option_id = selected_voice_option_id

        if playback_speed is not None:
            playback_session.playback_speed = playback_speed

        next_chunk_index = current_chunk_index
        if next_chunk_index is None:
            next_chunk_index = playback_session.current_chunk_index

        if current_chunk_index is not None or voice_option_id is not None:
            chunk = _get_document_chunk(
                session=session,
                document_id=playback_session.document_id,
                chunk_index=next_chunk_index,
            )
            if chunk is None:
                raise IndexError(
                    f"Chunk index {next_chunk_index} is out of range for playback session {session_id}"
                )

            engine_name, audio_path, _voice_model_name = _get_chunk_audio_path(
                document_id=playback_session.document_id,
                chunk=chunk,
                voice_option_id=selected_voice_option_id,
                user_id=playback_session.user_id if user_id is None else user_id,
            )
            playback_session.chunk_id = chunk.id
            playback_session.current_chunk_index = next_chunk_index
            playback_session.engine_name = engine_name
            playback_session.audio_path = str(audio_path)
            upsert_document_progress(
                session=session,
                document_id=playback_session.document_id,
                current_chunk_index=next_chunk_index,
            )

        session.flush()
        return _build_playback_session_result(session=session, playback_session=playback_session)


def update_playback_session_progress(*, session_id: int, current_chunk_index: int) -> PlaybackSessionResult:
    return update_playback_session(session_id=session_id, current_chunk_index=current_chunk_index)


def prebuffer_playback_session(*, session_id: int, user_id: int | None = None) -> PlaybackPrebufferResult:
    with db.session_scope() as session:
        playback_session = session.get(PlaybackSession, session_id)
        if playback_session is None or (user_id is not None and playback_session.user_id != user_id):
            raise LookupError(f"Playback session {session_id} was not found")

        target_chunk_index = playback_session.current_chunk_index + 1
        chunk = _get_document_chunk(
            session=session,
            document_id=playback_session.document_id,
            chunk_index=target_chunk_index,
        )
        if chunk is None:
            return PlaybackPrebufferResult(
                session_id=session_id,
                target_chunk_index=None,
                status="end_of_document",
                audio_url=None,
            )

        selected_voice_option_id = playback_session.voice_option_id or get_voice_settings(
            user_id=playback_session.user_id if user_id is None else user_id
        ).default_live_voice_id
        _, audio_path, _voice_model_name = _get_chunk_audio_path(
            document_id=playback_session.document_id,
            chunk=chunk,
            voice_option_id=selected_voice_option_id,
            user_id=playback_session.user_id if user_id is None else user_id,
        )

        return PlaybackPrebufferResult(
            session_id=session_id,
            target_chunk_index=target_chunk_index,
            status="prepared",
            audio_url=f"/api/playback/audio/{session_id}?prebuffer={target_chunk_index}",
            detail=audio_path.name,
        )


def get_playback_audio_path(*, session_id: int, user_id: int | None = None) -> Path:
    with db.session_scope() as session:
        playback_session = session.get(PlaybackSession, session_id)
        if playback_session is None or (user_id is not None and playback_session.user_id != user_id):
            raise ValueError(f"Playback session {session_id} was not found")

        audio_path = Path(playback_session.audio_path).resolve()
        allowed_cache_roots = [Path(settings.cache_root).resolve()]
        if playback_session.user_id is not None:
            allowed_cache_roots.append(user_cache_root(playback_session.user_id).resolve())
        if not any(audio_path.is_relative_to(cache_root) for cache_root in allowed_cache_roots):
            raise ValueError(f"Audio file for playback session {session_id} is outside the audio cache")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file for playback session {session_id} is missing")

        touch_cached_audio(audio_path)
        return audio_path
