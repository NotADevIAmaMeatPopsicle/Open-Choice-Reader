from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select

from app import db
from app.config import settings
from app.models.voice_preset import VoicePreset
from app.services.uploads import read_upload_bytes
from app.services.user_storage import user_voices_root


QWEN3_CLONE_ENGINE = "qwen3_clone"


def _voices_root(*, owner_user_id: int | None = None) -> Path:
    if owner_user_id is not None:
        root = user_voices_root(owner_user_id)
    else:
        root = Path(settings.storage_root) / "voices"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_reference_audio_path(filename: Path, *, owner_user_id: int | None = None) -> Path:
    stem = filename.stem or "voice"
    suffix = filename.suffix or ".wav"
    return _voices_root(owner_user_id=owner_user_id) / f"{stem}-{uuid4().hex}{suffix}"


def create_voice_preset(
    *,
    name: str,
    reference_audio: UploadFile,
    transcript: str,
    owner_user_id: int | None = None,
    source_provider: str | None = None,
    source_url: str | None = None,
    transcript_source_url: str | None = None,
    license_label: str | None = None,
    provenance_note: str | None = None,
) -> VoicePreset:
    cleaned_transcript = transcript.strip()
    if not cleaned_transcript:
        raise ValueError("transcript is required")

    filename = Path(reference_audio.filename or "reference.wav")
    destination = _build_reference_audio_path(filename, owner_user_id=owner_user_id)

    try:
        with destination.open("xb") as output:
            output.write(read_upload_bytes(reference_audio, max_bytes=settings.voice_upload_max_bytes))

        voice_preset = VoicePreset(
            owner_user_id=owner_user_id,
            name=name,
            engine=QWEN3_CLONE_ENGINE,
            reference_path=str(destination),
            transcript=cleaned_transcript,
            source_provider=source_provider,
            source_url=source_url,
            transcript_source_url=transcript_source_url,
            license_label=license_label,
            provenance_note=provenance_note,
        )

        with db.session_scope() as session:
            session.add(voice_preset)
            session.flush()
            session.refresh(voice_preset)

        return voice_preset
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def list_voice_presets(*, owner_user_id: int | None = None) -> list[VoicePreset]:
    with db.session_scope() as session:
        statement = select(VoicePreset).order_by(VoicePreset.id)
        if owner_user_id is not None:
            statement = statement.where(VoicePreset.owner_user_id == owner_user_id)
        return list(session.scalars(statement))
