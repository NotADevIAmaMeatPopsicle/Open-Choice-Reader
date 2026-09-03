export const MIN_PLAYBACK_SPEED = 0.5;
export const MAX_PLAYBACK_SPEED = 8;
export const PLAYBACK_SPEED_STEP = 0.05;

export function clampPlaybackSpeed(value: number) {
  if (!Number.isFinite(value)) {
    return 1;
  }

  return Math.max(MIN_PLAYBACK_SPEED, Math.min(MAX_PLAYBACK_SPEED, Math.round(value * 20) / 20));
}
