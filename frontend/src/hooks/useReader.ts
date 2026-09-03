import { useEffect, useMemo, useState } from "react";

import { prebufferPlaybackSession } from "../api/client";
import { useSettings } from "./useSettings";
import { activatePlaybackSession, usePlayer } from "./usePlayer";

type UseReaderOptions = {
  sessionId: string;
};

export function useReader({ sessionId }: UseReaderOptions) {
  const player = usePlayer();
  const settings = useSettings();
  const [prebufferStatus, setPrebufferStatus] = useState<string | null>(null);
  const [prebufferError, setPrebufferError] = useState<string | null>(null);

  useEffect(() => {
    void activatePlaybackSession(sessionId);
  }, [sessionId]);

  const liveVoiceOptions = useMemo(
    () => settings.voiceOptions.filter((voiceOption) => voiceOption.supports_live_reading),
    [settings.voiceOptions],
  );
  const activeSession = player.activeSession && String(player.activeSession.id) === sessionId ? player.activeSession : null;
  const selectedVoiceId =
    activeSession?.voice_option_id ?? settings.settings?.default_live_voice_id ?? liveVoiceOptions[0]?.id ?? "";

  useEffect(() => {
    if (!activeSession?.voice_option_id?.startsWith("preset:")) {
      setPrebufferStatus(null);
      setPrebufferError(null);
      return;
    }

    let isCurrent = true;
    setPrebufferStatus("preparing");
    setPrebufferError(null);

    void prebufferPlaybackSession(String(activeSession.id))
      .then((result) => {
        if (!isCurrent) {
          return;
        }
        setPrebufferStatus(result.status);
      })
      .catch((error) => {
        if (!isCurrent) {
          return;
        }
        setPrebufferStatus("failed");
        setPrebufferError(error instanceof Error ? error.message : "Unable to prebuffer cloned voice");
      });

    return () => {
      isCurrent = false;
    };
  }, [activeSession?.id, activeSession?.current_chunk_index, activeSession?.voice_option_id]);

  return {
    activeSession,
    advanceProgress: player.advanceProgress,
    audioSource: player.audioSource,
    currentChunkIndex: activeSession?.current_chunk_index ?? 0,
    error: player.error,
    isHydrating: player.isHydrating,
    isPlaying: player.isPlaying,
    isVoiceSettingsLoading: settings.isLoading,
    liveVoiceOptions,
    playbackSpeed: activeSession?.playback_speed ?? 1,
    prebufferError,
    prebufferStatus,
    sectionChunks: activeSession?.section_chunks ?? [],
    seekRelative: player.seekRelative,
    selectedVoiceId,
    setIsPlaying: player.setIsPlaying,
    sessionTitle: activeSession?.document_title ?? "Reading progress",
    togglePlayback: player.togglePlayback,
    updateProgressIndex: async (nextChunkIndex: number) => {
      return player.updateSession({ current_chunk_index: nextChunkIndex });
    },
    updatePlaybackSpeed: async (nextSpeed: number) => {
      return player.updateSession({ playback_speed: nextSpeed });
    },
    updateVoiceOption: async (voiceOptionId: string) => {
      return player.updateSession({ voice_option_id: voiceOptionId }, { autoplay: player.isPlaying });
    },
    voiceSettingsError: settings.error,
  };
}
