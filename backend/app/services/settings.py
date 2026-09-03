from dataclasses import dataclass
import platform
import shutil
import subprocess

from sqlalchemy import select

from app import db
from app.config import settings
from app.models.app_setting import AppSetting
from app.models.user_setting import UserSetting
from app.services.themes import DEFAULT_THEME_ID, ThemeSnapshot, get_theme, theme_exists
from app.tts.base import EngineStatus, VoiceOption
from app.tts.registry import (
    list_engine_statuses,
    list_voice_options,
    normalize_clone_engine_id,
    resolve_voice_option,
)


DEFAULT_LIVE_VOICE_KEY = "default_live_voice_id"
DEFAULT_EXPORT_VOICE_KEY = "default_export_voice_id"
FALLBACK_VOICE_KEY = "fallback_voice_id"
SELECTED_CLONE_MODEL_KEY = "selected_clone_model_engine"
ACTIVE_THEME_ID_KEY = "active_theme_id"
UI_THEME_KEY = "ui_theme"
SIDEBAR_WIDTH_KEY = "sidebar_width_px"
SIDEBAR_MODE_KEY = "sidebar_mode"
DOCK_POSITION_KEY = "dock_position"
TOOLTIPS_ENABLED_KEY = "tooltips_enabled"
DEFAULT_PLAYBACK_SPEED_KEY = "default_playback_speed"
LIVE_NARRATION_PACE_KEY = "live_narration_pace"
AUTO_PAUSE_ON_INTERRUPT_KEY = "auto_pause_on_interrupt"
LIBRARY_VIEW_MODE_KEY = "library_view_mode"
BACKGROUND_OVERRIDE_THEME_ID_KEY = "background_override_theme_id"
SHELF_OVERRIDE_THEME_ID_KEY = "shelf_override_theme_id"

DEFAULT_UI_THEME = DEFAULT_THEME_ID
DEFAULT_SIDEBAR_WIDTH_PX = 196
DEFAULT_SIDEBAR_MODE = "expanded"
DEFAULT_DOCK_POSITION = "bottom"
DEFAULT_TOOLTIPS_ENABLED = True
DEFAULT_PLAYBACK_SPEED = 1.0
DEFAULT_AUTO_PAUSE_ON_INTERRUPT = True
DEFAULT_LIBRARY_VIEW_MODE = "cover"
VALID_DOCK_POSITIONS = {"bottom", "top-left", "top-center", "top-right"}
VALID_SIDEBAR_MODES = {"expanded", "icon"}
VALID_LIBRARY_VIEW_MODES = {"cover", "spine"}
ICON_SIDEBAR_WIDTH_PX = 74
EXPANDED_SIDEBAR_WIDTH_PX = 196
MIN_PLAYBACK_SPEED = 0.5
MAX_PLAYBACK_SPEED = 8.0
DEFAULT_NARRATION_PACE = 1.0
MIN_NARRATION_PACE = 0.5
MAX_NARRATION_PACE = 2.0


@dataclass(frozen=True)
class VoiceSettingsSnapshot:
    active_theme_id: str
    active_theme: ThemeSnapshot
    default_live_voice_id: str
    default_export_voice_id: str
    fallback_voice_id: str | None
    selected_clone_model_engine: str
    engine_statuses: list[EngineStatus]
    host_runtime: "HostRuntimeSnapshot"
    clone_runtime: "CloneRuntimeSnapshot"
    ui_theme: str
    sidebar_width_px: int
    sidebar_mode: str
    dock_position: str
    tooltips_enabled: bool
    default_playback_speed: float
    live_narration_pace: float
    auto_pause_on_interrupt: bool
    library_view_mode: str
    background_override_theme_id: str | None
    shelf_override_theme_id: str | None


@dataclass(frozen=True)
class HostRuntimeSnapshot:
    host_name: str
    runtime_label: str
    gpu_name: str | None
    execution_summary: str


@dataclass(frozen=True)
class CloneRuntimeSnapshot:
    engine: str
    model_name: str
    preset_count: int
    availability: str
    availability_detail: str
    usage_summary: str
    execution_summary: str
    available_models: list["CloneRuntimeModelSnapshot"]


@dataclass(frozen=True)
class CloneRuntimeModelSnapshot:
    engine: str
    display_name: str
    model_name: str
    availability: str
    availability_detail: str


def get_voice_settings(*, user_id: int | None = None) -> VoiceSettingsSnapshot:
    voice_options = list_voice_options(user_id=user_id)
    engine_statuses = list_engine_statuses()

    with db.session_scope() as session:
        setting_model = UserSetting if user_id is not None else AppSetting
        statement = select(setting_model).where(
            setting_model.key.in_(
                (
                    ACTIVE_THEME_ID_KEY,
                    DEFAULT_LIVE_VOICE_KEY,
                    DEFAULT_EXPORT_VOICE_KEY,
                    FALLBACK_VOICE_KEY,
                    SELECTED_CLONE_MODEL_KEY,
                    UI_THEME_KEY,
                    SIDEBAR_WIDTH_KEY,
                    SIDEBAR_MODE_KEY,
                    DOCK_POSITION_KEY,
                    TOOLTIPS_ENABLED_KEY,
                    DEFAULT_PLAYBACK_SPEED_KEY,
                    LIVE_NARRATION_PACE_KEY,
                    AUTO_PAUSE_ON_INTERRUPT_KEY,
                    LIBRARY_VIEW_MODE_KEY,
                    BACKGROUND_OVERRIDE_THEME_ID_KEY,
                    SHELF_OVERRIDE_THEME_ID_KEY,
                )
            )
        )
        if user_id is not None:
            statement = statement.where(setting_model.user_id == user_id)

        stored_values = {
            setting.key: setting.value
            for setting in session.scalars(statement)
        }

    active_theme_id = _coerce_active_theme_id(stored_values, user_id=user_id)
    active_theme = get_theme(active_theme_id, owner_user_id=user_id)
    default_live_voice_id = _coerce_default_live_voice_id(stored_values.get(DEFAULT_LIVE_VOICE_KEY), voice_options)
    default_export_voice_id = _coerce_default_export_voice_id(stored_values.get(DEFAULT_EXPORT_VOICE_KEY), voice_options)
    fallback_voice_id = _coerce_fallback_voice_id(
        stored_value=stored_values.get(FALLBACK_VOICE_KEY),
        has_stored_value=FALLBACK_VOICE_KEY in stored_values,
        voice_options=voice_options,
    )
    selected_clone_model_engine = _coerce_selected_clone_model_engine(stored_values.get(SELECTED_CLONE_MODEL_KEY))
    sidebar_mode = _coerce_sidebar_mode(stored_values.get(SIDEBAR_MODE_KEY))
    sidebar_width_px = _coerce_sidebar_width(stored_values.get(SIDEBAR_WIDTH_KEY), sidebar_mode)
    dock_position = _coerce_dock_position(stored_values.get(DOCK_POSITION_KEY))
    tooltips_enabled = _coerce_boolean_setting(stored_values.get(TOOLTIPS_ENABLED_KEY), default=DEFAULT_TOOLTIPS_ENABLED)
    default_playback_speed = _coerce_playback_speed(stored_values.get(DEFAULT_PLAYBACK_SPEED_KEY))
    live_narration_pace = _coerce_narration_pace(stored_values.get(LIVE_NARRATION_PACE_KEY))
    auto_pause_on_interrupt = _coerce_boolean_setting(
        stored_values.get(AUTO_PAUSE_ON_INTERRUPT_KEY),
        default=DEFAULT_AUTO_PAUSE_ON_INTERRUPT,
    )
    library_view_mode = _coerce_library_view_mode(stored_values.get(LIBRARY_VIEW_MODE_KEY))
    background_override_theme_id = _coerce_theme_override_id(
        stored_values.get(BACKGROUND_OVERRIDE_THEME_ID_KEY),
        user_id=user_id,
    )
    shelf_override_theme_id = _coerce_theme_override_id(
        stored_values.get(SHELF_OVERRIDE_THEME_ID_KEY),
        user_id=user_id,
    )

    from app.services.voice_presets import list_voice_presets

    voice_presets = list_voice_presets(owner_user_id=user_id)
    host_runtime = _build_host_runtime_snapshot()
    clone_runtime = _build_clone_runtime_snapshot(
        engine_statuses=engine_statuses,
        preset_count=len(voice_presets),
        host_runtime=host_runtime,
        selected_clone_model_engine=selected_clone_model_engine,
    )

    return VoiceSettingsSnapshot(
        active_theme_id=active_theme_id,
        active_theme=active_theme,
        default_live_voice_id=default_live_voice_id,
        default_export_voice_id=default_export_voice_id,
        fallback_voice_id=fallback_voice_id,
        selected_clone_model_engine=selected_clone_model_engine,
        engine_statuses=engine_statuses,
        host_runtime=host_runtime,
        clone_runtime=clone_runtime,
        ui_theme=active_theme_id,
        sidebar_width_px=sidebar_width_px,
        sidebar_mode=sidebar_mode,
        dock_position=dock_position,
        tooltips_enabled=tooltips_enabled,
        default_playback_speed=default_playback_speed,
        live_narration_pace=live_narration_pace,
        auto_pause_on_interrupt=auto_pause_on_interrupt,
        library_view_mode=library_view_mode,
        background_override_theme_id=background_override_theme_id,
        shelf_override_theme_id=shelf_override_theme_id,
    )


def update_voice_settings(
    *,
    user_id: int | None = None,
    active_theme_id: str | None = None,
    default_live_voice_id: str,
    default_export_voice_id: str,
    fallback_voice_id: str | None,
    selected_clone_model_engine: str,
    ui_theme: str | None = None,
    sidebar_width_px: int | None = None,
    sidebar_mode: str | None = None,
    dock_position: str | None = None,
    tooltips_enabled: bool | None = None,
    default_playback_speed: float | None = None,
    live_narration_pace: float | None = None,
    auto_pause_on_interrupt: bool | None = None,
    library_view_mode: str | None = None,
    background_override_theme_id: str | None = None,
    shelf_override_theme_id: str | None = None,
) -> VoiceSettingsSnapshot:
    voice_options = list_voice_options(user_id=user_id)
    normalized_clone_model_engine = normalize_clone_engine_id(selected_clone_model_engine)
    normalized_active_theme_id = _coerce_requested_active_theme_id(
        active_theme_id=active_theme_id,
        ui_theme=ui_theme,
        user_id=user_id,
    )
    normalized_sidebar_mode = _coerce_sidebar_mode(sidebar_mode)
    normalized_sidebar_width = _coerce_sidebar_width(sidebar_width_px, normalized_sidebar_mode)
    normalized_dock_position = _coerce_dock_position(dock_position)
    normalized_tooltips_enabled = (
        DEFAULT_TOOLTIPS_ENABLED if tooltips_enabled is None else bool(tooltips_enabled)
    )
    normalized_playback_speed = _coerce_playback_speed(default_playback_speed)
    normalized_narration_pace = _coerce_narration_pace(live_narration_pace)
    normalized_auto_pause = (
        DEFAULT_AUTO_PAUSE_ON_INTERRUPT if auto_pause_on_interrupt is None else bool(auto_pause_on_interrupt)
    )
    normalized_library_view_mode = _coerce_library_view_mode(library_view_mode)
    normalized_background_override_theme_id = _coerce_theme_override_id(
        background_override_theme_id,
        user_id=user_id,
    )
    normalized_shelf_override_theme_id = _coerce_theme_override_id(
        shelf_override_theme_id,
        user_id=user_id,
    )

    _require_voice_option(
        voice_option_id=default_live_voice_id,
        voice_options=voice_options,
        setting_name="default live reading voice",
        required_capability="supports_live_reading",
    )
    _require_voice_option(
        voice_option_id=default_export_voice_id,
        voice_options=voice_options,
        setting_name="default export voice",
        required_capability="supports_export",
    )

    if fallback_voice_id:
        _require_voice_option(
            voice_option_id=fallback_voice_id,
            voice_options=voice_options,
            setting_name="fallback voice",
            required_capability=None,
        )

    with db.session_scope() as session:
        _upsert_setting(session=session, user_id=user_id, key=ACTIVE_THEME_ID_KEY, value=normalized_active_theme_id)
        _upsert_setting(session=session, user_id=user_id, key=UI_THEME_KEY, value=normalized_active_theme_id)
        _upsert_setting(session=session, user_id=user_id, key=DEFAULT_LIVE_VOICE_KEY, value=default_live_voice_id)
        _upsert_setting(session=session, user_id=user_id, key=DEFAULT_EXPORT_VOICE_KEY, value=default_export_voice_id)
        _upsert_setting(session=session, user_id=user_id, key=FALLBACK_VOICE_KEY, value=fallback_voice_id)
        _upsert_setting(session=session, user_id=user_id, key=SELECTED_CLONE_MODEL_KEY, value=normalized_clone_model_engine)
        _upsert_setting(session=session, user_id=user_id, key=SIDEBAR_WIDTH_KEY, value=str(normalized_sidebar_width))
        _upsert_setting(session=session, user_id=user_id, key=SIDEBAR_MODE_KEY, value=normalized_sidebar_mode)
        _upsert_setting(session=session, user_id=user_id, key=DOCK_POSITION_KEY, value=normalized_dock_position)
        _upsert_setting(
            session=session,
            user_id=user_id,
            key=TOOLTIPS_ENABLED_KEY,
            value="true" if normalized_tooltips_enabled else "false",
        )
        _upsert_setting(
            session=session,
            user_id=user_id,
            key=DEFAULT_PLAYBACK_SPEED_KEY,
            value=f"{normalized_playback_speed:.2f}",
        )
        _upsert_setting(
            session=session,
            user_id=user_id,
            key=LIVE_NARRATION_PACE_KEY,
            value=f"{normalized_narration_pace:.2f}",
        )
        _upsert_setting(
            session=session,
            user_id=user_id,
            key=AUTO_PAUSE_ON_INTERRUPT_KEY,
            value="true" if normalized_auto_pause else "false",
        )
        _upsert_setting(
            session=session,
            user_id=user_id,
            key=LIBRARY_VIEW_MODE_KEY,
            value=normalized_library_view_mode,
        )
        _upsert_setting(
            session=session,
            user_id=user_id,
            key=BACKGROUND_OVERRIDE_THEME_ID_KEY,
            value=normalized_background_override_theme_id,
        )
        _upsert_setting(
            session=session,
            user_id=user_id,
            key=SHELF_OVERRIDE_THEME_ID_KEY,
            value=normalized_shelf_override_theme_id,
        )

    return get_voice_settings(user_id=user_id)


def set_active_theme(theme_id: str, *, user_id: int | None = None) -> VoiceSettingsSnapshot:
    normalized_theme_id = _coerce_requested_active_theme_id(
        active_theme_id=theme_id,
        ui_theme=None,
        user_id=user_id,
    )

    with db.session_scope() as session:
        _upsert_setting(session=session, user_id=user_id, key=ACTIVE_THEME_ID_KEY, value=normalized_theme_id)
        _upsert_setting(session=session, user_id=user_id, key=UI_THEME_KEY, value=normalized_theme_id)

    return get_voice_settings(user_id=user_id)


def get_default_playback_speed(*, user_id: int | None = None) -> float:
    return get_voice_settings(user_id=user_id).default_playback_speed


def get_live_narration_pace(*, user_id: int | None = None) -> float:
    with db.session_scope() as session:
        if user_id is not None:
            setting = session.get(UserSetting, {"user_id": user_id, "key": LIVE_NARRATION_PACE_KEY})
        else:
            setting = session.get(AppSetting, LIVE_NARRATION_PACE_KEY)
        stored_value = setting.value if setting is not None else None

    return _coerce_narration_pace(stored_value)


def _upsert_setting(*, session, user_id: int | None, key: str, value: str | None) -> None:
    if user_id is None:
        setting = session.get(AppSetting, key)
        if setting is None:
            session.add(AppSetting(key=key, value=value))
            return

        setting.value = value
        return

    setting = session.get(UserSetting, {"user_id": user_id, "key": key})
    if setting is None:
        session.add(UserSetting(user_id=user_id, key=key, value=value))
        return

    setting.value = value


def _coerce_default_live_voice_id(stored_value: str | None, voice_options: list[VoiceOption]) -> str:
    if stored_value:
        stored_option = resolve_voice_option(stored_value)
        if (
            stored_option is not None
            and stored_option.supports_live_reading
            and stored_option.availability == "available"
        ):
            return stored_value

    for voice_option in voice_options:
        if (
            voice_option.voice_type == "built_in"
            and voice_option.supports_live_reading
            and voice_option.availability == "available"
        ):
            return voice_option.id

    for voice_option in voice_options:
        if voice_option.supports_live_reading:
            return voice_option.id

    raise ValueError("No live-reading voice options are available")


def _coerce_default_export_voice_id(stored_value: str | None, voice_options: list[VoiceOption]) -> str:
    if stored_value:
        stored_option = resolve_voice_option(stored_value)
        if stored_option is not None and stored_option.supports_export:
            return stored_value

    for voice_option in voice_options:
        if (
            voice_option.voice_type == "built_in"
            and voice_option.engine == "piper"
            and voice_option.supports_export
            and voice_option.availability == "available"
        ):
            return voice_option.id

    for voice_option in voice_options:
        if voice_option.supports_export and voice_option.availability == "available":
            return voice_option.id

    for voice_option in voice_options:
        if voice_option.supports_export:
            return voice_option.id

    raise ValueError("No export voice options are available")


def _coerce_fallback_voice_id(
    *,
    stored_value: str | None,
    has_stored_value: bool,
    voice_options: list[VoiceOption],
) -> str | None:
    if has_stored_value and stored_value is None:
        return None

    if stored_value:
        stored_option = resolve_voice_option(stored_value)
        if stored_option is not None and stored_option.availability == "available":
            return stored_value

    for voice_option in voice_options:
        if (
            voice_option.voice_type == "built_in"
            and voice_option.supports_live_reading
            and voice_option.availability == "available"
        ):
            return voice_option.id

    return None


def _coerce_selected_clone_model_engine(stored_value: str | None) -> str:
    if stored_value:
        try:
            return normalize_clone_engine_id(stored_value)
        except ValueError:
            pass

    return "qwen3_clone_0_6b"


def _coerce_active_theme_id(stored_values: dict[str, str | None], *, user_id: int | None = None) -> str:
    candidate = stored_values.get(ACTIVE_THEME_ID_KEY) or stored_values.get(UI_THEME_KEY) or DEFAULT_THEME_ID
    normalized = candidate.strip().lower() if isinstance(candidate, str) else DEFAULT_THEME_ID
    if theme_exists(normalized, owner_user_id=user_id):
        return normalized
    return DEFAULT_THEME_ID


def _coerce_requested_active_theme_id(
    *,
    active_theme_id: str | None,
    ui_theme: str | None,
    user_id: int | None = None,
) -> str:
    candidate = ui_theme or active_theme_id or DEFAULT_THEME_ID
    normalized = candidate.strip().lower()
    if not theme_exists(normalized, owner_user_id=user_id):
        raise ValueError(f"Unknown theme '{normalized}'")
    return normalized


def _coerce_sidebar_width(stored_value: str | int | None, sidebar_mode: str) -> int:
    if sidebar_mode == "icon":
        return ICON_SIDEBAR_WIDTH_PX

    try:
        candidate = int(stored_value) if stored_value is not None else EXPANDED_SIDEBAR_WIDTH_PX
    except (TypeError, ValueError):
        candidate = EXPANDED_SIDEBAR_WIDTH_PX

    if candidate <= ICON_SIDEBAR_WIDTH_PX:
        return EXPANDED_SIDEBAR_WIDTH_PX

    return EXPANDED_SIDEBAR_WIDTH_PX


def _coerce_sidebar_mode(stored_value: str | None) -> str:
    candidate = (stored_value or DEFAULT_SIDEBAR_MODE).strip().lower()
    if candidate == "compact":
        return "expanded"
    if candidate in VALID_SIDEBAR_MODES:
        return candidate
    return DEFAULT_SIDEBAR_MODE


def _coerce_dock_position(stored_value: str | None) -> str:
    candidate = (stored_value or DEFAULT_DOCK_POSITION).strip().lower()
    if candidate in VALID_DOCK_POSITIONS:
        return candidate
    return DEFAULT_DOCK_POSITION


def _coerce_library_view_mode(stored_value: str | None) -> str:
    candidate = (stored_value or DEFAULT_LIBRARY_VIEW_MODE).strip().lower()
    if candidate in VALID_LIBRARY_VIEW_MODES:
        return candidate
    return DEFAULT_LIBRARY_VIEW_MODE


def _coerce_theme_override_id(stored_value: str | None, *, user_id: int | None = None) -> str | None:
    if stored_value is None:
        return None

    candidate = stored_value.strip().lower()
    if not candidate:
        return None
    if theme_exists(candidate, owner_user_id=user_id):
        return candidate
    return None


def _coerce_playback_speed(stored_value: str | float | None) -> float:
    try:
        candidate = float(stored_value) if stored_value is not None else DEFAULT_PLAYBACK_SPEED
    except (TypeError, ValueError):
        candidate = DEFAULT_PLAYBACK_SPEED

    candidate = max(MIN_PLAYBACK_SPEED, min(MAX_PLAYBACK_SPEED, candidate))
    return round(candidate / 0.05) * 0.05


def _coerce_narration_pace(stored_value: str | float | None) -> float:
    try:
        candidate = float(stored_value) if stored_value is not None else DEFAULT_NARRATION_PACE
    except (TypeError, ValueError):
        candidate = DEFAULT_NARRATION_PACE

    candidate = max(MIN_NARRATION_PACE, min(MAX_NARRATION_PACE, candidate))
    return round(candidate / 0.05) * 0.05


def _coerce_boolean_setting(stored_value: str | None, *, default: bool) -> bool:
    if stored_value is None:
        return default

    normalized = stored_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _require_voice_option(
    *,
    voice_option_id: str,
    voice_options: list[VoiceOption],
    setting_name: str,
    required_capability: str | None,
) -> None:
    for voice_option in voice_options:
        if voice_option.id != voice_option_id:
            continue

        if required_capability is not None and not getattr(voice_option, required_capability):
            raise ValueError(f"{setting_name.capitalize()} does not support this voice")
        return

    raise ValueError(f"Unknown {setting_name} '{voice_option_id}'")


def _build_host_runtime_snapshot() -> HostRuntimeSnapshot:
    host_name = (platform.node() or "Unknown host").strip() or "Unknown host"
    gpu_name = _detect_gpu_name()

    if gpu_name:
        runtime_label = "GPU-capable host"
    else:
        runtime_label = "Local or CPU host"

    return HostRuntimeSnapshot(
        host_name=host_name,
        runtime_label=runtime_label,
        gpu_name=gpu_name,
        execution_summary="This host is serving Open Choice Reader and performing audio generation here.",
    )


def _build_clone_runtime_snapshot(
    *,
    engine_statuses: list[EngineStatus],
    preset_count: int,
    host_runtime: HostRuntimeSnapshot,
    selected_clone_model_engine: str,
) -> CloneRuntimeSnapshot:
    qwen_statuses = [engine_status for engine_status in engine_statuses if engine_status.engine_family == "qwen3_clone"]
    primary_status = next(
        (engine_status for engine_status in qwen_statuses if engine_status.engine == selected_clone_model_engine),
        None,
    )
    if primary_status is None:
        fallback_model_name = (
            settings.qwen_clone_large_model_name
            if selected_clone_model_engine == "qwen3_clone_1_7b"
            else settings.qwen_clone_model_name
        )
        fallback_display_name = (
            "Premium clone 1.7B"
            if selected_clone_model_engine == "qwen3_clone_1_7b"
            else "Premium clone 0.6B"
        )
        primary_status = EngineStatus(
            engine=selected_clone_model_engine,
            display_name=fallback_display_name,
            availability="unavailable",
            availability_detail="Qwen3 clone runtime is not installed on this host.",
            supports_live_reading=False,
            supports_export=True,
            engine_family="qwen3_clone",
            model_name=fallback_model_name,
        )

    return CloneRuntimeSnapshot(
        engine="qwen3_clone",
        model_name=primary_status.model_name or settings.qwen_clone_model_name,
        preset_count=preset_count,
        availability=primary_status.availability,
        availability_detail=primary_status.availability_detail,
        usage_summary="Saved cloned presets can be used for live reading and audiobook export when the clone runtime is available.",
        execution_summary=f"Live cloned reading and audiobook exports run on {host_runtime.host_name} when the clone runtime is available.",
        available_models=[
            CloneRuntimeModelSnapshot(
                engine=engine_status.engine,
                display_name=engine_status.display_name,
                model_name=engine_status.model_name or "",
                availability=engine_status.availability,
                availability_detail=engine_status.availability_detail,
            )
            for engine_status in qwen_statuses
        ],
    )


def _detect_gpu_name() -> str | None:
    if shutil.which("nvidia-smi") is None:
        return None

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            check=False,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None

    output = result.stdout.strip().splitlines()
    if not output:
        return None

    gpu_name = output[0].strip()
    return gpu_name or None
