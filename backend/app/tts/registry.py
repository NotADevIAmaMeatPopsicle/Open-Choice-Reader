import logging
from pathlib import Path

from app import db
from app.models.app_setting import AppSetting
from app.models.user_setting import UserSetting
from app.config import settings
from app.tts.base import EngineStatus, TTSEngine, VoiceOption
from app.tts.kokoro_engine import KOKORO_VOICES, KokoroEngine
from app.tts.mock_engine import MockEngine
from app.tts.piper_engine import PiperEngine
from app.tts.qwen_clone_engine import Qwen3CloneEngine

logger = logging.getLogger(__name__)

SUPPORTED_CLONE_ENGINE_IDS = ("qwen3_clone_0_6b", "qwen3_clone_1_7b")


def get_tts_engine(name: str | None = None) -> TTSEngine:
    engine_name = (name or settings.tts_engine).strip().lower()

    if engine_name == "mock":
        return MockEngine()

    if engine_name == "kokoro":
        return _build_kokoro_engine()

    if engine_name == "piper":
        return _build_piper_engine()

    if engine_name in {"qwen3_clone", "qwen3_clone_0_6b"}:
        return _build_qwen_clone_engine(model_name=settings.qwen_clone_model_name)

    if engine_name == "qwen3_clone_1_7b":
        return _build_qwen_clone_engine(model_name=settings.qwen_clone_large_model_name)

    raise ValueError(f"Unknown TTS engine '{engine_name}'")


def list_engine_statuses() -> list[EngineStatus]:
    return [
        _build_kokoro_engine().get_engine_status(),
        _build_piper_engine().get_engine_status(),
        _build_qwen_clone_engine(model_name=settings.qwen_clone_model_name).get_engine_status(),
        _build_qwen_clone_engine(model_name=settings.qwen_clone_large_model_name).get_engine_status(),
    ]


def list_voice_options(*, user_id: int | None = None) -> list[VoiceOption]:
    voice_options = [
        *_build_kokoro_engine().list_voice_options(),
        *_build_piper_engine().list_voice_options(),
    ]
    selected_clone_engine_id = _resolve_selected_clone_engine_id(user_id=user_id)
    qwen_status = build_clone_engine_for_profile(selected_clone_engine_id).get_engine_status()

    from app.services.voice_presets import list_voice_presets

    for preset in list_voice_presets(owner_user_id=user_id):
        preset_has_transcript = bool((preset.transcript or "").strip())
        preset_has_reference_audio = Path(preset.reference_path).is_file()
        voice_options.append(
            VoiceOption(
                id=f"preset:{preset.id}",
                name=preset.name,
                voice_type="cloned",
                engine=preset.engine,
                mode_label="Cloned voice",
                description="Saved reference voice preset for premium live reading and audiobook export.",
                availability=qwen_status.availability,
                availability_detail=_preset_availability_detail(preset, qwen_status),
                supports_live_reading=preset_has_transcript and preset_has_reference_audio,
                supports_export=preset_has_transcript and preset_has_reference_audio,
                transcript_preview=_transcript_preview(preset.transcript),
                engine_family="qwen3_clone",
                model_name=qwen_status.model_name,
            )
        )

    return sorted(voice_options, key=_voice_option_sort_key)


def resolve_voice_option(voice_option_id: str, *, user_id: int | None = None) -> VoiceOption | None:
    normalized_voice_option_id = voice_option_id.strip()
    if not normalized_voice_option_id:
        return None

    for voice_option in list_voice_options(user_id=user_id):
        if voice_option.id == normalized_voice_option_id:
            return voice_option

    return None


def build_live_engine_for_voice_option(
    voice_option_id: str | None,
    *,
    user_id: int | None = None,
    pace: float = 1.0,
) -> TTSEngine:
    runtime_engine = get_tts_engine()

    if not voice_option_id:
        return runtime_engine

    voice_option = resolve_voice_option(voice_option_id, user_id=user_id)
    if voice_option is None:
        return runtime_engine

    if runtime_engine.name == "mock" and voice_option.availability != "available":
        return runtime_engine

    if voice_option.engine_family == "kokoro":
        return _build_kokoro_engine(voice_option_id=voice_option.id, pace=pace)
    if voice_option.engine_family == "piper":
        return _build_piper_engine(voice_option_id=voice_option.id, pace=pace)
    if voice_option.engine_family == "qwen3_clone" and voice_option.id.startswith("preset:"):
        preset = _resolve_voice_preset_for_option_id(voice_option.id, user_id=user_id)
        if preset is None:
            return runtime_engine
        selected_clone_engine_id = _resolve_selected_clone_engine_id(user_id=user_id)
        clone_engine = build_clone_engine_for_profile(selected_clone_engine_id)
        return Qwen3CloneEngine(
            model_name=clone_engine.model_name,
            reference_audio_path=Path(preset.reference_path),
            transcript=preset.transcript,
        )

    return runtime_engine


def build_clone_engine_for_profile(clone_engine_id: str | None) -> Qwen3CloneEngine:
    normalized_clone_engine_id = normalize_clone_engine_id(clone_engine_id)
    if normalized_clone_engine_id == "qwen3_clone_1_7b":
        return _build_qwen_clone_engine(model_name=settings.qwen_clone_large_model_name)
    return _build_qwen_clone_engine(model_name=settings.qwen_clone_model_name)


def normalize_clone_engine_id(clone_engine_id: str | None) -> str:
    normalized_clone_engine_id = (clone_engine_id or "").strip() or "qwen3_clone_0_6b"
    if normalized_clone_engine_id not in SUPPORTED_CLONE_ENGINE_IDS:
        raise ValueError(f"Unsupported clone engine '{normalized_clone_engine_id}'")
    return normalized_clone_engine_id


def _resolve_selected_clone_engine_id(*, user_id: int | None = None) -> str:
    try:
        with db.session_scope() as session:
            if user_id is not None:
                selected_clone_setting = session.get(
                    UserSetting,
                    {"user_id": user_id, "key": "selected_clone_model_engine"},
                )
                if selected_clone_setting is not None:
                    return normalize_clone_engine_id(selected_clone_setting.value)
            selected_clone_setting = session.get(AppSetting, "selected_clone_model_engine")
            return normalize_clone_engine_id(selected_clone_setting.value if selected_clone_setting else None)
    except Exception:
        logger.warning(
            "Falling back to the default clone engine because the selected clone engine setting could not be read",
            exc_info=True,
        )
        return normalize_clone_engine_id(None)


def _resolve_voice_preset_for_option_id(voice_option_id: str, *, user_id: int | None = None):
    if not voice_option_id.startswith("preset:"):
        return None

    try:
        preset_id = int(voice_option_id.replace("preset:", "", 1))
    except ValueError:
        return None

    from app.services.voice_presets import list_voice_presets

    for preset in list_voice_presets(owner_user_id=user_id):
        if preset.id == preset_id:
            return preset

    return None


def _build_kokoro_engine(*, voice_option_id: str | None = None, pace: float = 1.0) -> KokoroEngine:
    base_engine = KokoroEngine(
        model_path=settings.kokoro_model_path,
        voices_path=settings.kokoro_voices_path,
        binary=settings.kokoro_binary,
    )
    return KokoroEngine(
        model_path=settings.kokoro_model_path,
        voices_path=settings.kokoro_voices_path,
        binary=settings.kokoro_binary,
        voice_name=base_engine.resolve_voice_name_for_voice_option(voice_option_id),
        pace=pace,
    )


def _build_piper_engine(*, voice_option_id: str | None = None, pace: float = 1.0) -> PiperEngine:
    base_engine = PiperEngine(
        model_path=settings.piper_model_path,
        binary=settings.piper_binary,
    )
    return PiperEngine(
        model_path=base_engine.resolve_model_path_for_voice_option(voice_option_id),
        binary=settings.piper_binary,
        pace=pace,
    )


def _build_qwen_clone_engine(*, model_name: str) -> Qwen3CloneEngine:
    return Qwen3CloneEngine(model_name=model_name)


def _preset_availability_detail(preset, qwen_status: EngineStatus) -> str:
    transcript = (preset.transcript or "").strip()
    if not transcript:
        return f"Voice preset {preset.id} is missing its transcript."

    if not Path(preset.reference_path).is_file():
        return f"Voice preset {preset.id} is missing its reference audio."

    return qwen_status.availability_detail


def _transcript_preview(transcript: str | None) -> str | None:
    cleaned_transcript = (transcript or "").strip()
    return cleaned_transcript or None


def _voice_option_sort_key(voice_option: VoiceOption) -> tuple[int, int, int, str]:
    availability_rank = 0 if voice_option.availability == "available" else 1
    voice_type_rank = 0 if voice_option.voice_type == "built_in" else 1
    engine_rank = {
        "kokoro": 0,
        "piper": 1,
        "qwen3_clone": 2,
    }.get(voice_option.engine_family or voice_option.engine, 99)
    within_engine_rank = _voice_option_within_engine_rank(voice_option)
    return (availability_rank, voice_type_rank, engine_rank, within_engine_rank)


def _voice_option_within_engine_rank(voice_option: VoiceOption) -> str:
    if voice_option.engine_family == "kokoro":
        kokoro_order = {
            f"builtin:kokoro:{voice_name.replace('_', '-')}": index
            for index, (voice_name, _display_name) in enumerate(KOKORO_VOICES)
        }
        return f"{kokoro_order.get(voice_option.id, 999):03d}"

    return voice_option.name.lower()
