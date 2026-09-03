from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import UploadFile

from app.config import settings
from app.services.uploads import read_upload_bytes


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

        return _transcribe_audio_path(audio_path)


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
    try:
        module = import_module("faster_whisper")
    except ModuleNotFoundError as error:
        raise RuntimeError("Local transcription runtime is not installed. Install faster-whisper on this host.") from error

    model_class = getattr(module, "WhisperModel", None)
    if model_class is None:
        raise RuntimeError("Local transcription runtime does not expose WhisperModel")

    return model_class(
        settings.voice_transcription_model_name,
        device=settings.voice_transcription_device,
        compute_type=settings.voice_transcription_compute_type,
    )
