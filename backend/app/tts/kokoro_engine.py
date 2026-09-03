from importlib import import_module
from pathlib import Path

from app.tts.base import EngineStatus, TTSEngine, VoiceOption


KOKORO_MODEL_NAME = "Kokoro-82M ONNX"

KOKORO_VOICES: tuple[tuple[str, str], ...] = (
    ("af_heart", "Heart"),
    ("af_bella", "Bella"),
    ("af_nicole", "Nicole"),
    ("af_sarah", "Sarah"),
    ("af_sky", "Sky"),
    ("am_michael", "Michael"),
)


class KokoroEngine(TTSEngine):
    name = "kokoro"
    mode_label = "Natural reader"
    voice_description = "Higher-quality local Kokoro narrator for primary live reading."
    unavailable_voice_detail = "Kokoro needs its runtime, model, and voice bundle before this narrator can run."
    unavailable_engine_detail = "Kokoro needs its runtime, model, and voice bundle before live reading can start."

    def __init__(
        self,
        *,
        model_path: str | Path,
        voices_path: str | Path,
        binary: str = "kokoro-onnx",
        voice_name: str | None = None,
        pace: float = 1.0,
    ) -> None:
        self.model_path = Path(model_path)
        self.voices_path = Path(voices_path)
        self.binary = binary
        self.voice_name = voice_name or KOKORO_VOICES[0][0]
        self.pace = pace
        self._model = None

    def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
        kokoro_class = self._load_kokoro_class()
        if kokoro_class is None:
            raise RuntimeError("Kokoro Python runtime is not available")
        if not self.model_path.exists():
            raise RuntimeError(f"Kokoro model '{self.model_path}' was not found")
        if not self.voices_path.exists():
            raise RuntimeError(f"Kokoro voices bundle '{self.voices_path}' was not found")

        model = self._model or kokoro_class(str(self.model_path), str(self.voices_path))
        self._model = model

        output_path.parent.mkdir(parents=True, exist_ok=True)
        samples, sample_rate = model.create(text, voice=self.voice_name, speed=self.pace)
        import_module("soundfile").write(output_path, samples, sample_rate, format="WAV")
        return output_path

    def list_voice_options(self) -> list[VoiceOption]:
        runtime_ready = self._is_ready()
        return [
            VoiceOption(
                id=_build_voice_option_id(voice_name),
                name=display_name,
                voice_type="built_in",
                engine=self.name,
                mode_label=self.mode_label,
                description=self.voice_description,
                availability="available" if runtime_ready else "unavailable",
                availability_detail=(
                    f"Kokoro is ready with {len(KOKORO_VOICES)} built-in voices."
                    if runtime_ready
                    else self.unavailable_voice_detail
                ),
                supports_live_reading=True,
                supports_export=True,
                engine_family=self.name,
                model_name=KOKORO_MODEL_NAME,
            )
            for voice_name, display_name in KOKORO_VOICES
        ]

    def get_engine_status(self) -> EngineStatus:
        runtime_ready = self._is_ready()
        return EngineStatus(
            engine=self.name,
            display_name="Natural reader",
            availability="available" if runtime_ready else "unavailable",
            availability_detail=(
                f"Kokoro is ready with {len(KOKORO_VOICES)} built-in voices."
                if runtime_ready
                else self.unavailable_engine_detail
            ),
            supports_live_reading=True,
            supports_export=True,
            engine_family=self.name,
            model_name=KOKORO_MODEL_NAME,
            voice_count=len(KOKORO_VOICES),
        )

    def resolve_voice_name_for_voice_option(self, voice_option_id: str | None) -> str:
        if not voice_option_id:
            return self.voice_name

        for voice_name, _display_name in KOKORO_VOICES:
            if _build_voice_option_id(voice_name) == voice_option_id:
                return voice_name

        return self.voice_name

    def _is_ready(self) -> bool:
        return (
            self._load_kokoro_class() is not None
            and self.model_path.exists()
            and self.voices_path.exists()
        )

    def _load_kokoro_class(self):
        try:
            return getattr(import_module("kokoro_onnx"), "Kokoro", None)
        except ModuleNotFoundError:
            return None


def _build_voice_option_id(voice_name: str) -> str:
    return f"builtin:kokoro:{voice_name.replace('_', '-')}"
