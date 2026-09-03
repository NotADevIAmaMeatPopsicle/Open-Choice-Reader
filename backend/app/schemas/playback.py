from pydantic import BaseModel, ConfigDict, Field


class PlaybackSessionCreate(BaseModel):
    document_id: int
    start_section_id: int | None = None
    voice_option_id: str | None = None
    playback_speed: float | None = Field(default=None, ge=0.5, le=8.0)


class PlaybackSessionUpdate(BaseModel):
    current_chunk_index: int | None = Field(default=None, ge=0)
    playback_speed: float | None = Field(default=None, ge=0.5, le=8.0)
    voice_option_id: str | None = None


class PlaybackSectionChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_index: int
    text: str
    is_current: bool


class PlaybackSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    document_title: str
    document_author: str | None
    cover_url: str
    current_chunk_index: int
    total_chunks: int
    audio_url: str
    engine_name: str
    voice_option_id: str | None = None
    voice_model_name: str | None = None
    playback_speed: float
    current_chunk_text: str
    current_section_title: str | None = None
    section_chunks: list[PlaybackSectionChunkRead]


class PlaybackPrebufferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    target_chunk_index: int | None
    status: str
    audio_url: str | None = None
    detail: str | None = None
