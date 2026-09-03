from pathlib import Path

from app.services.audio_cache import build_voice_preview_audio_cache_path, populate_cached_audio
from app.tts.registry import build_live_engine_for_voice_option, resolve_voice_option


VOICE_PREVIEW_TEXT = (
    "Open Choice Reader narrator preview. This sample lets you hear the selected voice before making it the live default."
)


def get_voice_preview_audio_path(*, voice_option_id: str, user_id: int | None = None) -> Path:
    normalized_voice_option_id = voice_option_id.strip()
    if not normalized_voice_option_id:
        raise ValueError("voice_option_id is required")

    voice_option = resolve_voice_option(normalized_voice_option_id, user_id=user_id)
    if voice_option is None:
        raise LookupError(f"Unknown voice '{normalized_voice_option_id}'")
    if not voice_option.supports_live_reading:
        raise ValueError(f"Voice '{normalized_voice_option_id}' does not support preview")
    if voice_option.availability != "available":
        raise ValueError(voice_option.availability_detail)

    engine = build_live_engine_for_voice_option(normalized_voice_option_id, user_id=user_id)
    output_path = build_voice_preview_audio_cache_path(
        engine_name=engine.name,
        text=VOICE_PREVIEW_TEXT,
        voice_cache_key=normalized_voice_option_id,
    )
    populate_cached_audio(engine=engine, text=VOICE_PREVIEW_TEXT, output_path=output_path)
    return output_path
