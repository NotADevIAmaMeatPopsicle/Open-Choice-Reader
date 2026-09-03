import { useEffect, useState } from "react";

import { createVoicePreset, listVoiceOptions, listVoicePresets } from "../api/client";
import type { VoiceOptionRecord, VoicePresetRecord } from "../api/types";

type RefreshVoicesResult = {
  errorMessage: string | null;
  ok: boolean;
};

interface UseVoicesResult {
  builtInVoices: VoiceOptionRecord[];
  clonedVoiceOptions: VoiceOptionRecord[];
  createPreset: (name: string, transcript: string, referenceAudio: File) => Promise<boolean>;
  createError: string | null;
  isCreating: boolean;
  loadError: string | null;
  voiceOptions: VoiceOptionRecord[];
  voicePresets: VoicePresetRecord[];
  isLoading: boolean;
  refresh: () => Promise<RefreshVoicesResult>;
}

export function useVoices(): UseVoicesResult {
  const [voiceOptions, setVoiceOptions] = useState<VoiceOptionRecord[]>([]);
  const [voicePresets, setVoicePresets] = useState<VoicePresetRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  async function refresh(): Promise<RefreshVoicesResult> {
    setIsLoading(true);

    try {
      const [options, presets] = await Promise.all([listVoiceOptions(), listVoicePresets()]);
      setVoiceOptions(options);
      setVoicePresets(presets);
      setLoadError(null);
      return { errorMessage: null, ok: true };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load voice presets";
      setLoadError(message);
      return { errorMessage: message, ok: false };
    } finally {
      setIsLoading(false);
    }
  }

  async function createPreset(name: string, transcript: string, referenceAudio: File) {
    setIsCreating(true);
    setCreateError(null);

    try {
      await createVoicePreset(name, transcript, referenceAudio);
      const refreshResult = await refresh();
      if (!refreshResult.ok) {
        setCreateError(
          `Voice preset saved, but the preset list could not refresh. ${refreshResult.errorMessage}`,
        );
      }
      return true;
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "Unable to create voice preset");
      return false;
    } finally {
      setIsCreating(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  return {
    builtInVoices: voiceOptions.filter((voiceOption) => voiceOption.voice_type === "built_in"),
    clonedVoiceOptions: voiceOptions.filter((voiceOption) => voiceOption.voice_type === "cloned"),
    createError,
    createPreset,
    isCreating,
    loadError,
    voiceOptions,
    voicePresets,
    isLoading,
    refresh,
  };
}
