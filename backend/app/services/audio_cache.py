import os
import hashlib
import re
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.tts.base import TTSEngine


def build_chunk_audio_cache_path(
    *,
    engine_name: str,
    document_id: int,
    chunk_id: int,
    text: str,
    voice_cache_key: str | None = None,
) -> Path:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    cache_dir = Path(settings.cache_root) / "audio" / engine_name / _build_cache_scope(voice_cache_key) / str(document_id)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"chunk-{chunk_id}-{digest}.wav"


def build_voice_preview_audio_cache_path(
    *,
    engine_name: str,
    text: str,
    voice_cache_key: str | None = None,
) -> Path:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    cache_dir = Path(settings.cache_root) / "audio" / engine_name / "preview" / _build_cache_scope(voice_cache_key)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"preview-{digest}.wav"


def populate_cached_audio(*, engine: TTSEngine, text: str, output_path: Path) -> Path:
    if output_path.exists():
        return output_path

    temp_path = output_path.with_name(f"{output_path.name}.{uuid4().hex}.tmp")

    try:
        engine.synthesize_to_file(text=text, output_path=temp_path)
        os.replace(temp_path, output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return output_path


def populate_cached_clone_audio(
    *,
    engine,
    text: str,
    output_path: Path,
    reference_audio_path: Path,
    transcript: str,
) -> Path:
    if output_path.exists():
        return output_path

    temp_path = output_path.with_name(f"{output_path.name}.{uuid4().hex}.tmp")

    try:
        engine.clone_to_file(
            text=text,
            output_path=temp_path,
            reference_audio_path=reference_audio_path,
            transcript=transcript,
        )
        os.replace(temp_path, output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return output_path


def _build_cache_scope(voice_cache_key: str | None) -> str:
    if not voice_cache_key:
        return "default"

    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", voice_cache_key).strip("-").lower()
    return normalized or "default"
