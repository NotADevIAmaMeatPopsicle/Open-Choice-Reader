import shutil
import subprocess
import re
import sys
from pathlib import Path

from app.tts.base import EngineStatus, TTSEngine, VoiceOption


class PiperEngine(TTSEngine):
    name = "piper"
    mode_label = "Fast reader"
    voice_description = "Local Piper voice for quick read-aloud and fallback export."
    unavailable_voice_detail = "Piper needs a model file and binary before this voice can run."
    unavailable_engine_detail = "Piper needs a model file and binary before live reading can start."

    def __init__(self, *, model_path: str | Path, binary: str = "piper", pace: float = 1.0) -> None:
        self.model_path = Path(model_path)
        self.binary = binary
        self.pace = pace

    def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
        command = self._resolve_command()
        if command is None:
            raise RuntimeError(f"Piper binary '{self.binary}' is not available")
        if not self.model_path.exists():
            raise RuntimeError(f"Piper model '{self.model_path}' was not found")

        pace_arguments: list[str] = []
        if self.pace != 1.0:
            pace_arguments = ["--length_scale", f"{1 / self.pace:.3f}"]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                *command,
                "--model",
                str(self.model_path),
                "--output_file",
                str(output_path),
                *pace_arguments,
            ],
            input=text.encode("utf-8"),
            check=True,
        )
        return output_path

    def list_voice_options(self) -> list[VoiceOption]:
        binary_ready = self._resolve_command() is not None
        available_models = [model_path for model_path in self._catalog_model_paths() if model_path.exists()]
        ready_voice_count = len(available_models)
        voice_options: list[VoiceOption] = []

        for model_path in self._catalog_model_paths():
            voice_is_ready = binary_ready and model_path.exists()
            voice_options.append(
                VoiceOption(
                    id=self._build_voice_id(model_path),
                    name=self._build_voice_name(model_path),
                    voice_type="built_in",
                    engine=self.name,
                    mode_label=self.mode_label,
                    description=self.voice_description,
                    availability="available" if voice_is_ready else "unavailable",
                    availability_detail=(
                        _available_detail(ready_voice_count)
                        if voice_is_ready
                        else self.unavailable_voice_detail
                    ),
                    supports_live_reading=True,
                    supports_export=True,
                    engine_family=self.name,
                    model_name=None,
                )
            )

        return voice_options

    def get_engine_status(self) -> EngineStatus:
        binary_ready = self._resolve_command() is not None
        ready_voice_count = len([model_path for model_path in self._catalog_model_paths() if model_path.exists()])

        if binary_ready and ready_voice_count > 0:
            return EngineStatus(
                engine=self.name,
                display_name="Fast reader",
                availability="available",
                availability_detail=_available_detail(ready_voice_count),
                supports_live_reading=True,
                supports_export=True,
                engine_family=self.name,
                model_name=None,
                voice_count=len(self._catalog_model_paths()),
            )

        return EngineStatus(
            engine=self.name,
            display_name="Fast reader",
            availability="unavailable",
            availability_detail=self.unavailable_engine_detail,
            supports_live_reading=True,
            supports_export=True,
            engine_family=self.name,
            model_name=None,
            voice_count=len(self._catalog_model_paths()),
        )

    def resolve_model_path_for_voice_option(self, voice_option_id: str | None) -> Path:
        if not voice_option_id:
            return self.model_path

        for model_path in self._catalog_model_paths():
            if self._build_voice_id(model_path) == voice_option_id:
                return model_path

        return self.model_path

    def _resolve_binary_path(self) -> Path | None:
        discovered = shutil.which(self.binary)
        if discovered is not None:
            return Path(discovered)

        binary_path = Path(self.binary)
        if binary_path.is_absolute() and binary_path.exists():
            return binary_path

        sibling_binary = Path(sys.executable).resolve().parent / self.binary
        if sibling_binary.exists():
            return sibling_binary

        return None

    def _resolve_command(self) -> list[str] | None:
        binary_path = self._resolve_binary_path()
        if binary_path is not None:
            return [str(binary_path)]

        if Path(sys.executable).exists():
            return [str(Path(sys.executable)), "-m", "piper"]

        return None

    def _catalog_model_paths(self) -> list[Path]:
        candidate_directory = self.model_path.parent
        if candidate_directory.exists():
            discovered_models = sorted(candidate_directory.glob("*.onnx"))
            if discovered_models:
                return discovered_models

        return [self.model_path]

    def _build_voice_id(self, model_path: Path) -> str:
        return f"builtin:{self.name}:{_slugify(model_path.stem or 'default')}"

    def _build_voice_name(self, model_path: Path) -> str:
        stem = model_path.stem.strip()
        if not stem:
            return "Fast Reader"

        tokens = [token for token in re.split(r"[-_\s]+", stem) if token]
        if not tokens:
            return "Fast Reader"

        return " ".join(token.capitalize() for token in tokens)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return normalized or "default"


def _available_detail(voice_count: int) -> str:
    voice_label = "voice" if voice_count == 1 else "voices"
    return f"Piper is ready with {voice_count} local {voice_label}."
