from importlib import import_module
from pathlib import Path
from typing import Any

from app.tts.base import EngineStatus, TTSEngine


DEFAULT_QWEN_CLONE_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
DEFAULT_QWEN_CLONE_LARGE_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


class Qwen3CloneEngine(TTSEngine):
    name = "qwen3_clone"

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_QWEN_CLONE_MODEL,
        model_loader=None,
        model_kwargs: dict[str, Any] | None = None,
        language: str = "English",
        reference_audio_path: Path | None = None,
        transcript: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._model_loader = model_loader
        self._model_kwargs = model_kwargs or {}
        self._language = language
        self._reference_audio_path = reference_audio_path
        self._transcript = transcript
        self._model: Any | None = None
        self.name = _build_engine_key(model_name)

    def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
        if self._reference_audio_path is None or self._transcript is None:
            raise RuntimeError("Qwen3 clone synthesis requires a reference voice sample")

        return self.clone_to_file(
            text=text,
            output_path=output_path,
            reference_audio_path=self._reference_audio_path,
            transcript=self._transcript,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    def clone_to_file(
        self,
        *,
        text: str,
        output_path: Path,
        reference_audio_path: Path,
        transcript: str,
    ) -> Path:
        cleaned_transcript = transcript.strip()
        if not cleaned_transcript:
            raise ValueError("transcript is required for Qwen3 voice cloning")

        model = self._load_model()
        wavs, sample_rate = model.generate_voice_clone(
            text=text,
            language=self._language,
            ref_audio=str(reference_audio_path),
            ref_text=cleaned_transcript,
        )
        if not wavs:
            raise RuntimeError("Qwen3 voice clone returned no audio")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        _soundfile().write(output_path, wavs[0], sample_rate, format="WAV")
        return output_path

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        if self._model_loader is not None:
            self._model = self._model_loader()
            return self._model

        try:
            module = import_module("qwen_tts")
        except ModuleNotFoundError as error:
            raise RuntimeError("Qwen3 TTS runtime is not installed") from error

        model_class = getattr(module, "Qwen3TTSModel", None)
        if model_class is None:
            raise RuntimeError("qwen_tts does not expose Qwen3TTSModel")

        self._model = model_class.from_pretrained(self._model_name, **self._model_kwargs)
        return self._model

    def get_engine_status(self) -> EngineStatus:
        engine_key = _build_engine_key(self._model_name)
        display_name = _build_display_name(self._model_name)
        try:
            module = import_module("qwen_tts")
        except ModuleNotFoundError:
            return EngineStatus(
                engine=engine_key,
                display_name=display_name,
                availability="unavailable",
                availability_detail="Qwen3 clone runtime is not installed on this host.",
                supports_live_reading=True,
                supports_export=True,
                engine_family=Qwen3CloneEngine.name,
                model_name=self._model_name,
            )

        if getattr(module, "Qwen3TTSModel", None) is None:
            return EngineStatus(
                engine=engine_key,
                display_name=display_name,
                availability="unavailable",
                availability_detail="Qwen3 clone runtime is not installed on this host.",
                supports_live_reading=True,
                supports_export=True,
                engine_family=Qwen3CloneEngine.name,
                model_name=self._model_name,
            )

        return EngineStatus(
            engine=engine_key,
            display_name=display_name,
            availability="available",
            availability_detail="Qwen3 clone live reading and exports are ready when a saved preset is selected.",
            supports_live_reading=True,
            supports_export=True,
            engine_family=Qwen3CloneEngine.name,
            model_name=self._model_name,
        )


def _soundfile():
    return import_module("soundfile")


def _build_engine_key(model_name: str) -> str:
    if "1.7B" in model_name:
        return "qwen3_clone_1_7b"
    return "qwen3_clone_0_6b"


def _build_display_name(model_name: str) -> str:
    if "1.7B" in model_name:
        return "Premium clone 1.7B"
    return "Premium clone 0.6B"
