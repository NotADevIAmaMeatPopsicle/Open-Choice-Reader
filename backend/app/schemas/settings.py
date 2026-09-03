from pydantic import BaseModel, ConfigDict

from app.schemas.theme import ThemeProfileRead


class EngineStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    engine: str
    display_name: str
    availability: str
    availability_detail: str
    supports_live_reading: bool
    supports_export: bool
    engine_family: str = ""
    model_name: str | None = None
    voice_count: int = 0


class HostRuntimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    host_name: str
    runtime_label: str
    gpu_name: str | None = None
    execution_summary: str


class CloneRuntimeModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    engine: str
    display_name: str
    model_name: str
    availability: str
    availability_detail: str


class CloneRuntimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    engine: str
    model_name: str
    preset_count: int
    availability: str
    availability_detail: str
    usage_summary: str
    execution_summary: str
    available_models: list[CloneRuntimeModelRead]


class VoiceSettingsRead(BaseModel):
    active_theme_id: str
    active_theme: ThemeProfileRead
    default_live_voice_id: str
    default_export_voice_id: str
    fallback_voice_id: str | None = None
    selected_clone_model_engine: str
    engine_statuses: list[EngineStatusRead]
    host_runtime: HostRuntimeRead
    clone_runtime: CloneRuntimeRead
    ui_theme: str
    sidebar_width_px: int
    sidebar_mode: str
    dock_position: str
    tooltips_enabled: bool
    default_playback_speed: float
    live_narration_pace: float
    auto_pause_on_interrupt: bool
    library_view_mode: str
    background_override_theme_id: str | None = None
    shelf_override_theme_id: str | None = None


class VoiceSettingsUpdate(BaseModel):
    active_theme_id: str | None = None
    default_live_voice_id: str
    default_export_voice_id: str
    fallback_voice_id: str | None = None
    selected_clone_model_engine: str
    ui_theme: str | None = None
    sidebar_width_px: int | None = None
    sidebar_mode: str | None = None
    dock_position: str | None = None
    tooltips_enabled: bool | None = None
    default_playback_speed: float | None = None
    live_narration_pace: float | None = None
    auto_pause_on_interrupt: bool | None = None
    library_view_mode: str | None = None
    background_override_theme_id: str | None = None
    shelf_override_theme_id: str | None = None
