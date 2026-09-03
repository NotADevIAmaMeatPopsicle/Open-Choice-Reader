from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EngineStatus:
    engine: str
    display_name: str
    availability: str
    availability_detail: str
    supports_live_reading: bool
    supports_export: bool
    engine_family: str = ""
    model_name: str | None = None
    voice_count: int = 0


@dataclass(frozen=True)
class VoiceOption:
    id: str
    name: str
    voice_type: str
    engine: str
    mode_label: str
    description: str
    availability: str
    availability_detail: str
    supports_live_reading: bool
    supports_export: bool
    transcript_preview: str | None = None
    engine_family: str = ""
    model_name: str | None = None


class TTSEngine(ABC):
    name: str

    @abstractmethod
    def synthesize_to_file(self, *, text: str, output_path: Path) -> Path:
        raise NotImplementedError
