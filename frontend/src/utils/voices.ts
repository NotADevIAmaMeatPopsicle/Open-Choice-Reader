import type { VoiceOptionRecord } from "../api/types";

function toTitleCase(value: string) {
  return value
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function fallbackVoiceName(voiceOptionId?: string | null) {
  if (!voiceOptionId) {
    return "Default narrator";
  }

  if (voiceOptionId.startsWith("preset:")) {
    return "Saved cloned voice";
  }

  const idSegments = voiceOptionId.split(":");
  return toTitleCase(idSegments[idSegments.length - 1] ?? voiceOptionId);
}

export function fallbackVoiceEngineName(voiceOptionId?: string | null) {
  if (!voiceOptionId) {
    return "Default";
  }

  if (voiceOptionId.startsWith("preset:")) {
    return "Qwen3 Clone";
  }

  const idSegments = voiceOptionId.split(":");
  if (idSegments[0] === "builtin" && idSegments[1]) {
    return toTitleCase(idSegments[1]);
  }

  return toTitleCase(idSegments[idSegments.length - 2] ?? voiceOptionId);
}

export function resolveVoiceOption(
  voiceOptionId: string | null | undefined,
  options: VoiceOptionRecord[] = [],
) {
  return options.find((option) => option.id === voiceOptionId) ?? null;
}

export function resolveVoiceName(voiceOptionId: string | null | undefined, options: VoiceOptionRecord[] = []) {
  const selectedVoice = resolveVoiceOption(voiceOptionId, options);
  return selectedVoice?.name ?? fallbackVoiceName(voiceOptionId);
}

export function resolveVoiceEngineName(
  voiceOptionId: string | null | undefined,
  options: VoiceOptionRecord[] = [],
) {
  const selectedVoice = resolveVoiceOption(voiceOptionId, options);
  return toTitleCase(selectedVoice?.engine_family ?? selectedVoice?.engine ?? fallbackVoiceEngineName(voiceOptionId));
}

export function resolveVoiceCapabilityLabel(voiceOption: VoiceOptionRecord | null | undefined) {
  if (!voiceOption) {
    return "Unavailable";
  }

  if (voiceOption.supports_live_reading && voiceOption.supports_export) {
    return "Live + Export";
  }

  if (voiceOption.supports_live_reading) {
    return "Live";
  }

  if (voiceOption.supports_export) {
    return "Export";
  }

  return "Unavailable";
}
