import { useEffect, useState } from "react";

import { getPlaybackSession, prebufferPlaybackSession, updatePlaybackSession } from "../api/client";
import type { PlaybackSessionRecord, PlaybackSessionUpdatePayload } from "../api/types";
import { clampPlaybackSpeed } from "../utils/playbackSpeed";

const ACTIVE_SESSION_STORAGE_KEY = "open-choice-reader:active-session-id";
let activeSessionStorageKey = ACTIVE_SESSION_STORAGE_KEY;

type PlayerState = {
  activeSession: PlaybackSessionRecord | null;
  error: string | null;
  isBuffering: boolean;
  isHydrating: boolean;
  isPlaying: boolean;
  isMuted: boolean;
  volume: number;
};

type SetActiveSessionOptions = {
  autoplay?: boolean;
};

type PlayerSnapshot = PlayerState & {
  advanceProgress: () => Promise<boolean>;
  audioSource: string;
  bindAudioElement: (element: HTMLAudioElement | null) => void;
  hydrateStoredSession: () => Promise<void>;
  nudgePlaybackSpeed: (delta: number) => void;
  seekRelative: (seconds: number) => void;
  setActiveSession: (session: PlaybackSessionRecord | null, options?: SetActiveSessionOptions) => void;
  setIsPlaying: (nextValue: boolean) => void;
  setMuted: (nextValue: boolean) => void;
  setVolume: (nextValue: number) => void;
  togglePlayback: () => Promise<void>;
  toggleMuted: () => void;
  updateSession: (payload: PlaybackSessionUpdatePayload, options?: SetActiveSessionOptions) => Promise<PlaybackSessionRecord | null>;
};

const INITIAL_STATE: PlayerState = {
  activeSession: null,
  error: null,
  isBuffering: false,
  isHydrating: false,
  isMuted: false,
  isPlaying: false,
  volume: 0.85,
};

let playerState: PlayerState = INITIAL_STATE;
let audioElement: HTMLAudioElement | null = null;
let lastAudioSource = "";
let isAutoAdvancing = false;
let shouldResumeAfterSourceSync = false;
let hydrationPromise: Promise<void> | null = null;
let autoPauseOnInterrupt = true;
let hasBoundVisibilityListener = false;
let hasBoundKeyboardListener = false;
let pendingSeekOffsetSeconds: number | null = null;
let updateRequestCounter = 0;
let lastPrebufferKey = "";
let speedCommitTimer: ReturnType<typeof setTimeout> | null = null;

const listeners = new Set<(snapshot: PlayerSnapshot) => void>();

function normalizeSession(session: PlaybackSessionRecord): PlaybackSessionRecord {
  return {
    ...session,
    cover_url: session.cover_url ?? "",
    current_chunk_text: session.current_chunk_text ?? "",
    document_title: session.document_title ?? `Document ${session.document_id}`,
    playback_speed: session.playback_speed ?? 1,
    section_chunks: (session.section_chunks ?? []).map((chunk) => ({ ...chunk })),
    total_chunks: session.total_chunks ?? Math.max((session.current_chunk_index ?? 0) + 1, 1),
  };
}

function cloneState(): PlayerState {
  return {
    activeSession: playerState.activeSession ? normalizeSession(playerState.activeSession) : null,
    error: playerState.error,
    isBuffering: playerState.isBuffering,
    isHydrating: playerState.isHydrating,
    isMuted: playerState.isMuted,
    isPlaying: playerState.isPlaying,
    volume: playerState.volume,
  };
}

function buildAudioSource(session: PlaybackSessionRecord | null): string {
  if (!session) {
    return "";
  }

  const voiceKey = encodeURIComponent(session.voice_option_id ?? "default");
  return `${session.audio_url}?chunk=${session.current_chunk_index}&voice=${voiceKey}`;
}

function readStoredSessionId(): string | null {
  try {
    return window.localStorage.getItem(activeSessionStorageKey);
  } catch {
    return null;
  }
}

function writeStoredSessionId(sessionId: string | null) {
  try {
    if (!sessionId) {
      window.localStorage.removeItem(activeSessionStorageKey);
      return;
    }

    window.localStorage.setItem(activeSessionStorageKey, sessionId);
  } catch {
    // Local storage is best effort for resume; the app still functions without it.
  }
}

export function setPlayerStorageUserScope(userId: number | null) {
  activeSessionStorageKey = userId
    ? `open-choice-reader:user:${userId}:active-session-id`
    : ACTIVE_SESSION_STORAGE_KEY;
  playerState = {
    ...INITIAL_STATE,
    isMuted: playerState.isMuted,
    volume: playerState.volume,
  };
  lastAudioSource = "";
  shouldResumeAfterSourceSync = false;
  hydrationPromise = null;
  pendingSeekOffsetSeconds = null;
  updateRequestCounter += 1;
  lastPrebufferKey = "";
  clearPendingSpeedCommit();
  publish();
  syncAudioElement();
}

function publish() {
  const snapshot = createSnapshot();
  listeners.forEach((listener) => {
    listener(snapshot);
  });
}

function setPlayerState(nextState: Partial<PlayerState>) {
  playerState = {
    ...playerState,
    ...nextState,
  };
  publish();
}

function syncAudioElement() {
  if (!audioElement) {
    return;
  }

  const activeSession = playerState.activeSession;
  if (!activeSession) {
    if (!/jsdom/i.test(window.navigator.userAgent)) {
      try {
        audioElement.pause();
      } catch {
        // Browser media pause can still fail transiently; leave the element detached.
      }
    }
    audioElement.removeAttribute("src");
    lastAudioSource = "";
    audioElement.muted = playerState.isMuted;
    audioElement.playbackRate = 1;
    audioElement.volume = playerState.volume;
    return;
  }

  const nextAudioSource = buildAudioSource(activeSession);
  audioElement.muted = playerState.isMuted;
  audioElement.playbackRate = activeSession.playback_speed;
  audioElement.volume = playerState.volume;

  if (audioElement.src !== nextAudioSource && lastAudioSource !== nextAudioSource) {
    lastAudioSource = nextAudioSource;
    audioElement.src = nextAudioSource;

    if (!/jsdom/i.test(window.navigator.userAgent)) {
      try {
        audioElement.load();
      } catch {
        // Test runtimes may omit media loading support; browsers will handle it.
      }
    }
  }

  if (shouldResumeAfterSourceSync || playerState.isPlaying) {
    shouldResumeAfterSourceSync = false;
    void audioElement.play().catch(() => {
      setPlayerState({ isPlaying: false });
    });
  }
}

function shouldIgnoreKeyboardEvent(event: KeyboardEvent): boolean {
  if (event.ctrlKey || event.metaKey || event.altKey) {
    return true;
  }

  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  if (target.isContentEditable) {
    return true;
  }

  const tagName = target.tagName;
  return tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT" || tagName === "BUTTON" || tagName === "A";
}

function ensureKeyboardListener() {
  if (hasBoundKeyboardListener) {
    return;
  }

  document.addEventListener("keydown", (event) => {
    if (!playerState.activeSession || shouldIgnoreKeyboardEvent(event)) {
      return;
    }

    if (event.key === " " || event.key === "Spacebar") {
      event.preventDefault();
      void togglePlayback();
      return;
    }

    if (event.key === "ArrowLeft") {
      event.preventDefault();
      seekPlayerRelative(event.shiftKey ? -30 : -5);
      return;
    }

    if (event.key === "ArrowRight") {
      event.preventDefault();
      seekPlayerRelative(event.shiftKey ? 30 : 5);
    }
  });
  hasBoundKeyboardListener = true;
}

function ensureVisibilityListener() {
  if (hasBoundVisibilityListener) {
    return;
  }

  const pauseForInterrupt = () => {
    if (!autoPauseOnInterrupt || !audioElement || !playerState.isPlaying) {
      return;
    }

    audioElement.pause();
  };

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      return;
    }

    pauseForInterrupt();
  });
  window.addEventListener("pagehide", pauseForInterrupt);
  hasBoundVisibilityListener = true;
}

function handleAudioPause() {
  if (isAutoAdvancing) {
    return;
  }

  if (playerState.isPlaying) {
    setPlayerState({ isPlaying: false });
  }
}

function handleAudioPlay() {
  if (!playerState.isPlaying) {
    setPlayerState({ isPlaying: true });
  }
}

function setBuffering(nextValue: boolean) {
  if (playerState.isBuffering !== nextValue) {
    setPlayerState({ isBuffering: nextValue });
  }
}

function handleAudioWaiting() {
  setBuffering(true);
}

function handleAudioReady() {
  setBuffering(false);
}

function clearPendingSpeedCommit() {
  if (speedCommitTimer !== null) {
    clearTimeout(speedCommitTimer);
    speedCommitTimer = null;
  }
}

function schedulePrebuffer() {
  const activeSession = playerState.activeSession;
  if (!activeSession || activeSession.current_chunk_index >= activeSession.total_chunks - 1) {
    return;
  }

  const prebufferKey = `${activeSession.id}:${activeSession.current_chunk_index}:${activeSession.voice_option_id ?? "default"}`;
  if (prebufferKey === lastPrebufferKey) {
    return;
  }

  lastPrebufferKey = prebufferKey;
  void prebufferPlaybackSession(String(activeSession.id)).catch(() => {
    // Prebuffer is a lookahead optimization; playback still works without it.
  });
}

function getChunkBoundaryState() {
  const activeSession = playerState.activeSession;
  if (!activeSession) {
    return null;
  }

  return {
    currentChunkIndex: activeSession.current_chunk_index,
    hasNextChunk: activeSession.current_chunk_index < activeSession.total_chunks - 1,
    hasPreviousChunk: activeSession.current_chunk_index > 0,
  };
}

function continuePendingSeekAcrossChunks() {
  if (!audioElement || pendingSeekOffsetSeconds === null) {
    return;
  }

  const boundaryState = getChunkBoundaryState();
  if (!boundaryState) {
    pendingSeekOffsetSeconds = null;
    return;
  }

  const duration = audioElement.duration;
  if (!Number.isFinite(duration) || duration <= 0) {
    pendingSeekOffsetSeconds = null;
    return;
  }

  if (pendingSeekOffsetSeconds < 0) {
    const targetTime = duration + pendingSeekOffsetSeconds;
    if (targetTime >= 0) {
      audioElement.currentTime = targetTime;
      pendingSeekOffsetSeconds = null;
      return;
    }

    if (!boundaryState.hasPreviousChunk) {
      audioElement.currentTime = 0;
      pendingSeekOffsetSeconds = null;
      return;
    }

    pendingSeekOffsetSeconds = targetTime;
    void updateActivePlaybackSession(
      { current_chunk_index: boundaryState.currentChunkIndex - 1 },
      { autoplay: playerState.isPlaying },
    );
    return;
  }

  if (pendingSeekOffsetSeconds > duration) {
    if (!boundaryState.hasNextChunk) {
      audioElement.currentTime = duration;
      pendingSeekOffsetSeconds = null;
      return;
    }

    pendingSeekOffsetSeconds -= duration;
    void updateActivePlaybackSession(
      { current_chunk_index: boundaryState.currentChunkIndex + 1 },
      { autoplay: playerState.isPlaying },
    );
    return;
  }

  audioElement.currentTime = pendingSeekOffsetSeconds;
  pendingSeekOffsetSeconds = null;
}

function handleAudioLoadedMetadata() {
  continuePendingSeekAcrossChunks();
}

async function handleAudioEnded() {
  if (!playerState.activeSession) {
    setPlayerState({ isPlaying: false });
    return;
  }

  isAutoAdvancing = true;
  const advanced = await advanceProgress();
  isAutoAdvancing = false;

  if (!advanced) {
    setPlayerState({ isPlaying: false });
  }
}

export function bindAudioElement(element: HTMLAudioElement | null) {
  if (audioElement === element) {
    return;
  }

  if (audioElement) {
    audioElement.removeEventListener("ended", handleAudioEnded);
    audioElement.removeEventListener("pause", handleAudioPause);
    audioElement.removeEventListener("play", handleAudioPlay);
    audioElement.removeEventListener("loadedmetadata", handleAudioLoadedMetadata);
    audioElement.removeEventListener("waiting", handleAudioWaiting);
    audioElement.removeEventListener("stalled", handleAudioWaiting);
    audioElement.removeEventListener("canplay", handleAudioReady);
    audioElement.removeEventListener("playing", handleAudioReady);
    audioElement.removeEventListener("emptied", handleAudioReady);
  }

  audioElement = element;

  if (!audioElement) {
    return;
  }

  audioElement.addEventListener("ended", handleAudioEnded);
  audioElement.addEventListener("pause", handleAudioPause);
  audioElement.addEventListener("play", handleAudioPlay);
  audioElement.addEventListener("loadedmetadata", handleAudioLoadedMetadata);
  audioElement.addEventListener("waiting", handleAudioWaiting);
  audioElement.addEventListener("stalled", handleAudioWaiting);
  audioElement.addEventListener("canplay", handleAudioReady);
  audioElement.addEventListener("playing", handleAudioReady);
  audioElement.addEventListener("emptied", handleAudioReady);
  syncAudioElement();
}

export function setActivePlaybackSession(
  session: PlaybackSessionRecord | null,
  options: SetActiveSessionOptions = {},
) {
  if (!session) {
    writeStoredSessionId(null);
    lastAudioSource = "";
    shouldResumeAfterSourceSync = false;
    updateRequestCounter += 1;
    lastPrebufferKey = "";
    clearPendingSpeedCommit();
    playerState = INITIAL_STATE;
    publish();
    syncAudioElement();
    return;
  }

  writeStoredSessionId(String(session.id));
  shouldResumeAfterSourceSync = Boolean(options.autoplay);
  playerState = {
    ...playerState,
    activeSession: normalizeSession(session),
    error: null,
    isHydrating: false,
  };
  publish();
  syncAudioElement();
  schedulePrebuffer();
}

export async function hydrateStoredSession(): Promise<void> {
  if (playerState.activeSession || hydrationPromise) {
    return hydrationPromise ?? Promise.resolve();
  }

  const storedSessionId = readStoredSessionId();
  if (!storedSessionId) {
    return;
  }

  setPlayerState({ isHydrating: true });
  hydrationPromise = (async () => {
    try {
      const session = await getPlaybackSession(storedSessionId);
      setActivePlaybackSession(session);
    } catch {
      writeStoredSessionId(null);
      setPlayerState({ activeSession: null, error: null, isHydrating: false, isPlaying: false });
    } finally {
      hydrationPromise = null;
    }
  })();

  return hydrationPromise;
}

export async function activatePlaybackSession(sessionId: string, options: SetActiveSessionOptions = {}) {
  if (playerState.activeSession?.id === Number(sessionId)) {
    return playerState.activeSession;
  }

  setPlayerState({ isHydrating: true, error: null });

  try {
    const session = await getPlaybackSession(sessionId);
    setActivePlaybackSession(session, options);
    return session;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unable to load playback session";
    setPlayerState({ error: message, isHydrating: false });
    return null;
  }
}

export async function updateActivePlaybackSession(
  payload: PlaybackSessionUpdatePayload,
  options: SetActiveSessionOptions = {},
): Promise<PlaybackSessionRecord | null> {
  const activeSession = playerState.activeSession;
  if (!activeSession) {
    return null;
  }

  const requestId = ++updateRequestCounter;

  try {
    const nextSession = await updatePlaybackSession(String(activeSession.id), payload);
    if (requestId !== updateRequestCounter) {
      return nextSession;
    }
    setActivePlaybackSession(nextSession, { autoplay: options.autoplay ?? playerState.isPlaying });
    return nextSession;
  } catch (error) {
    if (requestId !== updateRequestCounter) {
      return null;
    }
    const message = error instanceof Error ? error.message : "Unable to update playback session";
    setPlayerState({ error: message });
    return null;
  }
}

export async function advanceProgress(): Promise<boolean> {
  const activeSession = playerState.activeSession;
  if (!activeSession) {
    return false;
  }

  if (activeSession.current_chunk_index >= activeSession.total_chunks - 1) {
    return false;
  }

  const nextSession = await updateActivePlaybackSession(
    {
      current_chunk_index: activeSession.current_chunk_index + 1,
    },
    { autoplay: true },
  );

  return nextSession?.current_chunk_index !== activeSession.current_chunk_index;
}

export async function togglePlayback(): Promise<void> {
  if (!audioElement) {
    if (!playerState.activeSession) {
      return;
    }

    shouldResumeAfterSourceSync = !playerState.isPlaying;
    setPlayerState({ isPlaying: !playerState.isPlaying });
    return;
  }

  if (playerState.isPlaying) {
    audioElement.pause();
    return;
  }

  try {
    await audioElement.play();
  } catch {
    setPlayerState({ isPlaying: false });
  }
}

export function setPlayerIsPlaying(nextValue: boolean) {
  setPlayerState({ isPlaying: nextValue });
}

export function setPlayerMuted(nextValue: boolean) {
  setPlayerState({ isMuted: nextValue });
  if (audioElement) {
    audioElement.muted = nextValue;
  }
}

export function togglePlayerMuted() {
  setPlayerMuted(!playerState.isMuted);
}

export function setPlayerVolume(nextValue: number) {
  const normalizedVolume = Math.max(0, Math.min(1, nextValue));
  setPlayerState({ volume: normalizedVolume });
  if (audioElement) {
    audioElement.volume = normalizedVolume;
  }
}

export function setAutoPauseOnInterruptPreference(nextValue: boolean) {
  autoPauseOnInterrupt = nextValue;
}

export function nudgePlaybackSpeed(delta: number) {
  const activeSession = playerState.activeSession;
  if (!activeSession) {
    return;
  }

  const nextSpeed = clampPlaybackSpeed(activeSession.playback_speed + delta);
  if (nextSpeed === activeSession.playback_speed) {
    return;
  }

  playerState = {
    ...playerState,
    activeSession: { ...activeSession, playback_speed: nextSpeed },
  };
  if (audioElement) {
    audioElement.playbackRate = nextSpeed;
  }
  publish();

  clearPendingSpeedCommit();
  speedCommitTimer = setTimeout(() => {
    speedCommitTimer = null;
    const latestSpeed = playerState.activeSession?.playback_speed;
    if (latestSpeed !== undefined) {
      void updateActivePlaybackSession({ playback_speed: latestSpeed });
    }
  }, 400);
}

export function seekPlayerRelative(seconds: number) {
  if (!audioElement || !playerState.activeSession) {
    return;
  }

  const currentTime = audioElement.currentTime;
  const duration = audioElement.duration;
  const targetTime = currentTime + seconds;
  const boundaryState = getChunkBoundaryState();

  if (!boundaryState) {
    return;
  }

  if (!Number.isFinite(duration) || duration <= 0) {
    audioElement.currentTime = Math.max(0, targetTime);
    return;
  }

  if (targetTime >= 0 && targetTime <= duration) {
    audioElement.currentTime = targetTime;
    return;
  }

  if (targetTime < 0) {
    if (!boundaryState.hasPreviousChunk) {
      audioElement.currentTime = 0;
      return;
    }

    pendingSeekOffsetSeconds = targetTime;
    void updateActivePlaybackSession(
      { current_chunk_index: boundaryState.currentChunkIndex - 1 },
      { autoplay: playerState.isPlaying },
    );
    return;
  }

  if (!boundaryState.hasNextChunk) {
    audioElement.currentTime = duration;
    return;
  }

  pendingSeekOffsetSeconds = targetTime - duration;
  void updateActivePlaybackSession(
    { current_chunk_index: boundaryState.currentChunkIndex + 1 },
    { autoplay: playerState.isPlaying },
  );
}

export function resetPlayerStateForTests() {
  playerState = INITIAL_STATE;
  activeSessionStorageKey = ACTIVE_SESSION_STORAGE_KEY;
  audioElement = null;
  lastAudioSource = "";
  isAutoAdvancing = false;
  shouldResumeAfterSourceSync = false;
  hydrationPromise = null;
  autoPauseOnInterrupt = true;
  hasBoundVisibilityListener = false;
  hasBoundKeyboardListener = false;
  pendingSeekOffsetSeconds = null;
  updateRequestCounter = 0;
  lastPrebufferKey = "";
  clearPendingSpeedCommit();
  listeners.clear();
}

function createSnapshot(): PlayerSnapshot {
  return {
    ...cloneState(),
    advanceProgress,
    audioSource: buildAudioSource(playerState.activeSession),
    bindAudioElement,
    hydrateStoredSession,
    nudgePlaybackSpeed,
    seekRelative: seekPlayerRelative,
    setActiveSession: setActivePlaybackSession,
    setIsPlaying: setPlayerIsPlaying,
    setMuted: setPlayerMuted,
    setVolume: setPlayerVolume,
    togglePlayback,
    toggleMuted: togglePlayerMuted,
    updateSession: updateActivePlaybackSession,
  };
}

export function usePlayer(): PlayerSnapshot {
  const [snapshot, setSnapshot] = useState<PlayerSnapshot>(createSnapshot);

  useEffect(() => {
    ensureVisibilityListener();
    ensureKeyboardListener();
    listeners.add(setSnapshot);
    return () => {
      listeners.delete(setSnapshot);
    };
  }, []);

  useEffect(() => {
    void hydrateStoredSession();
  }, []);

  return snapshot;
}
