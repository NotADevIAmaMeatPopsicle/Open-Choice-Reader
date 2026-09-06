from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore

from fastapi import UploadFile
import soundfile

from app.config import settings
from app.services.uploads import read_upload_bytes


_transcription_slots = BoundedSemaphore(value=settings.voice_transcription_max_concurrency)


@dataclass(frozen=True, slots=True)
class VoiceTranscriptionSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class VoiceTranscriptionResult:
    transcript: str
    language: str | None
    engine: str
    segments: list[VoiceTranscriptionSegment]


def transcribe_reference_audio(*, reference_audio: UploadFile) -> VoiceTranscriptionResult:
    suffix = Path(reference_audio.filename or "reference.wav").suffix or ".wav"

    with TemporaryDirectory(prefix="open-choice-reader-transcribe-") as temp_dir:
        audio_path = Path(temp_dir) / f"reference{suffix}"
        audio_path.write_bytes(read_upload_bytes(reference_audio, max_bytes=settings.voice_upload_max_bytes))

        if audio_path.stat().st_size == 0:
            raise ValueError("reference audio is empty")

        try:
            audio_info = soundfile.info(audio_path)
        except (RuntimeError, TypeError) as error:
            raise ValueError("reference audio could not be decoded") from error
        if audio_info.duration > settings.voice_transcription_max_seconds:
            raise ValueError(
                "reference audio exceeds the "
                f"{settings.voice_transcription_max_seconds:g}-second transcription limit"
            )

        if not _transcription_slots.acquire(blocking=False):
            raise RuntimeError("Local transcription is busy. Try again after the current request finishes.")
        try:
            return _transcribe_audio_path(audio_path)
        finally:
            _transcription_slots.release()


def _transcribe_audio_path(audio_path: Path) -> VoiceTranscriptionResult:
    model = _load_model()
    raw_segments, info = model.transcribe(str(audio_path), beam_size=5)

    segments = [
        VoiceTranscriptionSegment(
            start=float(getattr(segment, "start", 0.0)),
            end=float(getattr(segment, "end", 0.0)),
            text=str(getattr(segment, "text", "")).strip(),
        )
        for segment in raw_segments
        if str(getattr(segment, "text", "")).strip()
    ]
    transcript = " ".join(segment.text for segment in segments).strip()
    if not transcript:
        raise ValueError("local transcription returned no transcript")

    return VoiceTranscriptionResult(
        transcript=transcript,
        language=getattr(info, "language", None),
        engine=f"faster-whisper:{settings.voice_transcription_model_name}",
        segments=segments,
    )


def _load_model():
    return _load_model_for_runtime(
        settings.voice_transcription_model_name,
        settings.voice_transcription_device,
        settings.voice_transcription_compute_type,
    )


@lru_cache(maxsize=4)
def _load_model_for_runtime(model_name: str, device: str, compute_type: str):
    try:
        module = import_module("faster_whisper")
    except ModuleNotFoundError as error:
        raise RuntimeError("Local transcription runtime is not installed. Install faster-whisper on this host.") from error

    model_class = getattr(module, "WhisperModel", None)
    if model_class is None:
        raise RuntimeError("Local transcription runtime does not expose WhisperModel")

    return model_class(
        model_name,
        device=device,
        compute_type=compute_type,
    )
