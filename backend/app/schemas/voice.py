from pydantic import BaseModel, ConfigDict


class VoicePresetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    engine: str
    transcript: str
    source_provider: str | None = None
    source_url: str | None = None
    transcript_source_url: str | None = None
    license_label: str | None = None
    provenance_note: str | None = None


class VoiceOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class VoiceTranscriptionSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: float
    end: float
    text: str


class VoiceTranscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transcript: str
    language: str | None = None
    engine: str
    segments: list[VoiceTranscriptionSegmentRead]
