import { useEffect, useState } from "react";

import { getVoiceSettings, listVoiceOptions, updateVoiceSettings } from "../api/client";
import type { VoiceOptionRecord, VoiceSettingsRecord, VoiceSettingsUpdate } from "../api/types";

interface UseSettingsResult {
  error: string | null;
  isLoading: boolean;
  isSaving: boolean;
  saveSuccessMessage: string | null;
  settings: VoiceSettingsRecord | null;
  updateSettings: (nextSettings: Partial<VoiceSettingsUpdate>) => Promise<boolean>;
  voiceOptions: VoiceOptionRecord[];
}

export function useSettings(): UseSettingsResult {
  const [voiceOptions, setVoiceOptions] = useState<VoiceOptionRecord[]>([]);
  const [settings, setSettings] = useState<VoiceSettingsRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState<string | null>(null);

  async function refresh(): Promise<void> {
    setIsLoading(true);

    try {
      const [loadedVoiceOptions, loadedSettings] = await Promise.all([listVoiceOptions(), getVoiceSettings()]);
      setVoiceOptions(loadedVoiceOptions);
      setSettings(loadedSettings);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load voice settings");
    } finally {
      setIsLoading(false);
    }
  }

  async function updateSettingsValues(nextSettings: Partial<VoiceSettingsUpdate>): Promise<boolean> {
    if (!settings) {
      setError("Settings are not loaded yet.");
      return false;
    }

    setIsSaving(true);
    setSaveSuccessMessage(null);
    setError(null);

    try {
      const savedSettings = await updateVoiceSettings({
        active_theme_id: nextSettings.active_theme_id ?? settings.active_theme_id,
        default_export_voice_id: nextSettings.default_export_voice_id ?? settings.default_export_voice_id,
        default_live_voice_id: nextSettings.default_live_voice_id ?? settings.default_live_voice_id,
        fallback_voice_id:
          nextSettings.fallback_voice_id === undefined ? settings.fallback_voice_id : nextSettings.fallback_voice_id,
        selected_clone_model_engine:
          nextSettings.selected_clone_model_engine ?? settings.selected_clone_model_engine,
        ui_theme: nextSettings.ui_theme ?? settings.ui_theme,
        sidebar_width_px: nextSettings.sidebar_width_px ?? settings.sidebar_width_px,
        sidebar_mode: nextSettings.sidebar_mode ?? settings.sidebar_mode,
        dock_position: nextSettings.dock_position ?? settings.dock_position,
        tooltips_enabled: nextSettings.tooltips_enabled ?? settings.tooltips_enabled,
        default_playback_speed: nextSettings.default_playback_speed ?? settings.default_playback_speed,
        live_narration_pace: nextSettings.live_narration_pace ?? settings.live_narration_pace,
        auto_pause_on_interrupt:
          nextSettings.auto_pause_on_interrupt ?? settings.auto_pause_on_interrupt,
        library_view_mode: nextSettings.library_view_mode ?? settings.library_view_mode,
        background_override_theme_id:
          nextSettings.background_override_theme_id === undefined
            ? settings.background_override_theme_id
            : nextSettings.background_override_theme_id,
        shelf_override_theme_id:
          nextSettings.shelf_override_theme_id === undefined
            ? settings.shelf_override_theme_id
            : nextSettings.shelf_override_theme_id,
      });
      setSettings((currentSettings) => ({
        active_theme_id: savedSettings.active_theme_id ?? currentSettings?.active_theme_id ?? "ember",
        active_theme: savedSettings.active_theme ?? currentSettings?.active_theme ?? {
          id: "ember",
          name: "Ember",
          description: "Warm shelves, amber highlights, and the original house look.",
          source_kind: "house",
          source_label: "Open Choice Reader",
          source_reference: null,
          is_builtin: true,
          sort_order: 10,
          family: "house",
          preview_variant: "standard",
          background_asset_path: null,
          background_overlay_path: null,
          shelf_asset_path: null,
          surface_texture_asset_path: null,
          supports_mix_and_match: true,
          tokens: {},
        },
        default_export_voice_id: savedSettings.default_export_voice_id,
        default_live_voice_id: savedSettings.default_live_voice_id,
        fallback_voice_id: savedSettings.fallback_voice_id,
        selected_clone_model_engine:
          savedSettings.selected_clone_model_engine ?? currentSettings?.selected_clone_model_engine ?? "qwen3_clone_0_6b",
        engine_statuses: savedSettings.engine_statuses ?? currentSettings?.engine_statuses ?? [],
        host_runtime: savedSettings.host_runtime ?? currentSettings?.host_runtime ?? {
          execution_summary: "This host is serving Open Choice Reader and performing audio generation here.",
          gpu_name: null,
          host_name: "Unknown host",
          runtime_label: "Unknown runtime host",
        },
        clone_runtime: savedSettings.clone_runtime ?? currentSettings?.clone_runtime ?? {
          availability: "unknown",
          availability_detail: "Clone runtime details are unavailable until the host reports them.",
          engine: "qwen3_clone",
          execution_summary: "Cloned audiobook exports run on the connected host when the clone runtime is available.",
          model_name: "Unknown clone model",
          preset_count: 0,
          usage_summary: "Saved cloned presets are used for audiobook export, not instant live reading.",
          available_models: [],
        },
        ui_theme: savedSettings.ui_theme ?? currentSettings?.ui_theme ?? "ember",
        sidebar_width_px: savedSettings.sidebar_width_px ?? currentSettings?.sidebar_width_px ?? 196,
        sidebar_mode: savedSettings.sidebar_mode ?? currentSettings?.sidebar_mode ?? "expanded",
        dock_position: savedSettings.dock_position ?? currentSettings?.dock_position ?? "bottom",
        tooltips_enabled: savedSettings.tooltips_enabled ?? currentSettings?.tooltips_enabled ?? true,
        default_playback_speed:
          savedSettings.default_playback_speed ?? currentSettings?.default_playback_speed ?? 1,
        live_narration_pace: savedSettings.live_narration_pace ?? currentSettings?.live_narration_pace ?? 1,
        auto_pause_on_interrupt:
          savedSettings.auto_pause_on_interrupt ?? currentSettings?.auto_pause_on_interrupt ?? true,
        library_view_mode: savedSettings.library_view_mode ?? currentSettings?.library_view_mode ?? "cover",
        background_override_theme_id:
          savedSettings.background_override_theme_id === undefined
            ? currentSettings?.background_override_theme_id ?? null
            : savedSettings.background_override_theme_id,
        shelf_override_theme_id:
          savedSettings.shelf_override_theme_id === undefined
            ? currentSettings?.shelf_override_theme_id ?? null
            : savedSettings.shelf_override_theme_id,
      }));
      setSaveSuccessMessage("Voice settings saved.");
      return true;
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save voice settings");
      return false;
    } finally {
      setIsSaving(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    error,
    isLoading,
    isSaving,
    saveSuccessMessage,
    settings,
    updateSettings: updateSettingsValues,
    voiceOptions,
  };
}
