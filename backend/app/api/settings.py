from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import CurrentUser, get_current_user
from app.schemas.settings import VoiceSettingsRead, VoiceSettingsUpdate
from app.services.settings import get_voice_settings, update_voice_settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=VoiceSettingsRead)
def get_settings_route(current_user: CurrentUser = Depends(get_current_user)) -> VoiceSettingsRead:
    snapshot = get_voice_settings(user_id=current_user.id)
    return VoiceSettingsRead.model_validate(
        {
            "active_theme_id": snapshot.active_theme_id,
            "active_theme": snapshot.active_theme,
            "default_live_voice_id": snapshot.default_live_voice_id,
            "default_export_voice_id": snapshot.default_export_voice_id,
            "fallback_voice_id": snapshot.fallback_voice_id,
            "selected_clone_model_engine": snapshot.selected_clone_model_engine,
            "engine_statuses": snapshot.engine_statuses,
            "host_runtime": snapshot.host_runtime,
            "clone_runtime": snapshot.clone_runtime,
            "ui_theme": snapshot.ui_theme,
            "sidebar_width_px": snapshot.sidebar_width_px,
            "sidebar_mode": snapshot.sidebar_mode,
            "dock_position": snapshot.dock_position,
            "tooltips_enabled": snapshot.tooltips_enabled,
            "default_playback_speed": snapshot.default_playback_speed,
            "live_narration_pace": snapshot.live_narration_pace,
            "auto_pause_on_interrupt": snapshot.auto_pause_on_interrupt,
            "library_view_mode": snapshot.library_view_mode,
            "background_override_theme_id": snapshot.background_override_theme_id,
            "shelf_override_theme_id": snapshot.shelf_override_theme_id,
        }
    )


@router.put("", response_model=VoiceSettingsRead)
def update_settings_route(
    payload: VoiceSettingsUpdate,
    current_user: CurrentUser = Depends(get_current_user),
) -> VoiceSettingsRead:
    try:
        snapshot = update_voice_settings(
            user_id=current_user.id,
            active_theme_id=payload.active_theme_id,
            default_live_voice_id=payload.default_live_voice_id,
            default_export_voice_id=payload.default_export_voice_id,
            fallback_voice_id=payload.fallback_voice_id,
            selected_clone_model_engine=payload.selected_clone_model_engine,
            ui_theme=payload.ui_theme,
            sidebar_width_px=payload.sidebar_width_px,
            sidebar_mode=payload.sidebar_mode,
            dock_position=payload.dock_position,
            tooltips_enabled=payload.tooltips_enabled,
            default_playback_speed=payload.default_playback_speed,
            live_narration_pace=payload.live_narration_pace,
            auto_pause_on_interrupt=payload.auto_pause_on_interrupt,
            library_view_mode=payload.library_view_mode,
            background_override_theme_id=payload.background_override_theme_id,
            shelf_override_theme_id=payload.shelf_override_theme_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return VoiceSettingsRead.model_validate(
        {
            "active_theme_id": snapshot.active_theme_id,
            "active_theme": snapshot.active_theme,
            "default_live_voice_id": snapshot.default_live_voice_id,
            "default_export_voice_id": snapshot.default_export_voice_id,
            "fallback_voice_id": snapshot.fallback_voice_id,
            "selected_clone_model_engine": snapshot.selected_clone_model_engine,
            "engine_statuses": snapshot.engine_statuses,
            "host_runtime": snapshot.host_runtime,
            "clone_runtime": snapshot.clone_runtime,
            "ui_theme": snapshot.ui_theme,
            "sidebar_width_px": snapshot.sidebar_width_px,
            "sidebar_mode": snapshot.sidebar_mode,
            "dock_position": snapshot.dock_position,
            "tooltips_enabled": snapshot.tooltips_enabled,
            "default_playback_speed": snapshot.default_playback_speed,
            "live_narration_pace": snapshot.live_narration_pace,
            "auto_pause_on_interrupt": snapshot.auto_pause_on_interrupt,
            "library_view_mode": snapshot.library_view_mode,
            "background_override_theme_id": snapshot.background_override_theme_id,
            "shelf_override_theme_id": snapshot.shelf_override_theme_id,
        }
    )
