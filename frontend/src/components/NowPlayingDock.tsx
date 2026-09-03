import { useEffect, useRef } from "react";

import { IconGlyph } from "./IconGlyph";
import { usePlayer } from "../hooks/usePlayer";
import { useSettings } from "../hooks/useSettings";
import { resolveVoiceEngineName, resolveVoiceName } from "../utils/voices";

const SPEED_HOLD_DELAY_MS = 350;
const SPEED_HOLD_REPEAT_MS = 70;

type SpeedHoldState = {
  delayTimer: number | null;
  repeatTimer: number | null;
  didHold: boolean;
};

type NowPlayingDockVariant = "dock" | "popout";

type NowPlayingDockProps = {
  dockPosition: string;
  onNavigate: (pathname: string) => void;
  tooltipsEnabled: boolean;
  variant?: NowPlayingDockVariant;
};

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, value));
}

function maybeTitle(enabled: boolean, label: string) {
  return enabled ? label : undefined;
}

function formatPlaybackSpeed(value: number) {
  return `${value.toFixed(2).replace(/0+$/, "").replace(/\.$/, "")}x`;
}

export function NowPlayingDock({
  dockPosition,
  onNavigate,
  tooltipsEnabled,
  variant = "dock",
}: NowPlayingDockProps) {
  const { voiceOptions } = useSettings();
  const {
    activeSession,
    bindAudioElement,
    isBuffering,
    isPlaying,
    nudgePlaybackSpeed,
    seekRelative,
    setVolume,
    toggleMuted,
    togglePlayback,
    updateSession,
    volume,
  } = usePlayer();
  const progressPercent = activeSession
    ? clampPercent(((activeSession.current_chunk_index + 1) / Math.max(activeSession.total_chunks, 1)) * 100)
    : 0;
  const currentNarrator = activeSession ? resolveVoiceName(activeSession.voice_option_id, voiceOptions) : null;
  const currentEngine = activeSession ? resolveVoiceEngineName(activeSession.voice_option_id, voiceOptions) : null;
  const volumeTitle = `${Math.round(volume * 100)}% Volume`;
  const speedLabel = activeSession ? formatPlaybackSpeed(activeSession.playback_speed) : "1x";
  const dockClassName = [
    "now-playing-dock",
    `now-playing-dock--${variant}`,
    variant === "dock" ? `now-playing-dock--${dockPosition}` : "",
  ]
    .filter(Boolean)
    .join(" ");

  const speedHoldRef = useRef<SpeedHoldState>({ delayTimer: null, repeatTimer: null, didHold: false });

  const stopSpeedHold = () => {
    const holdState = speedHoldRef.current;
    if (holdState.delayTimer !== null) {
      window.clearTimeout(holdState.delayTimer);
      holdState.delayTimer = null;
    }
    if (holdState.repeatTimer !== null) {
      window.clearInterval(holdState.repeatTimer);
      holdState.repeatTimer = null;
    }
  };

  const startSpeedHold = (delta: number) => {
    stopSpeedHold();
    const holdState = speedHoldRef.current;
    holdState.didHold = false;
    holdState.delayTimer = window.setTimeout(() => {
      holdState.delayTimer = null;
      holdState.didHold = true;
      nudgePlaybackSpeed(delta);
      holdState.repeatTimer = window.setInterval(() => {
        nudgePlaybackSpeed(delta);
      }, SPEED_HOLD_REPEAT_MS);
    }, SPEED_HOLD_DELAY_MS);
  };

  const clickSpeed = (delta: number) => {
    const holdState = speedHoldRef.current;
    stopSpeedHold();
    if (holdState.didHold) {
      holdState.didHold = false;
      return;
    }
    nudgePlaybackSpeed(delta);
  };

  useEffect(() => stopSpeedHold, []);

  return (
    <div className={dockClassName} aria-label={variant === "popout" ? "Player window" : "Now playing dock"}>
      {activeSession ? (
        <>
          <div className="now-playing-dock__details">
            <p className="now-playing-dock__title">{activeSession.document_title}</p>
            <p className="now-playing-dock__subtitle">
              {activeSession.document_author ?? activeSession.current_section_title ?? "Ready to resume"}
            </p>
            <p className="now-playing-dock__voice">
              Narrator: {currentNarrator} | Engine: {currentEngine}
              {activeSession.voice_model_name ? ` | Model: ${activeSession.voice_model_name}` : ""}
            </p>
            <label className="now-playing-dock__progress-block">
              <span className="sr-only">Listening progress</span>
              <input
                aria-label="Listening progress"
                className="now-playing-dock__progress-slider"
                max={Math.max(activeSession.total_chunks - 1, 0)}
                min="0"
                onChange={(event) => {
                  void updateSession({
                    current_chunk_index: Number(event.target.value),
                  });
                }}
                step="1"
                type="range"
                value={activeSession.current_chunk_index}
              />
              <span className="now-playing-dock__progress-copy">{Math.round(progressPercent)}% complete</span>
            </label>
          </div>

          <div className="now-playing-dock__cover-wrap">
            <img
              alt={`Cover for ${activeSession.document_title}`}
              className="now-playing-dock__cover-image"
              src={activeSession.cover_url}
            />
          </div>

          <div className="now-playing-dock__transport">
            <div className="now-playing-dock__transport-meta">
              <span>
                Chunk {activeSession.current_chunk_index + 1} of {activeSession.total_chunks}
              </span>
              {isBuffering ? (
                <span className="now-playing-dock__buffering" role="status">
                  Preparing audio…
                </span>
              ) : null}
            </div>
            <div className="now-playing-dock__transport-controls">
              <button
                aria-label="Jump back 30 seconds"
                className="top-bar__icon-button now-playing-dock__transport-button"
                onClick={() => {
                  seekRelative(-30);
                }}
                title={maybeTitle(tooltipsEnabled, "Jump back 30 seconds")}
                type="button"
              >
                <IconGlyph name="seek-back-30" />
              </button>
              <button
                aria-label="Jump back 5 seconds"
                className="top-bar__icon-button now-playing-dock__transport-button"
                onClick={() => {
                  seekRelative(-5);
                }}
                title={maybeTitle(tooltipsEnabled, "Jump back 5 seconds")}
                type="button"
              >
                <IconGlyph name="seek-back-5" />
              </button>
              <button
                aria-label={isPlaying ? "Pause audio" : "Play audio"}
                className="top-bar__icon-button top-bar__icon-button--accent now-playing-dock__transport-button"
                onClick={() => {
                  void togglePlayback();
                }}
                title={maybeTitle(tooltipsEnabled, isPlaying ? "Pause audio" : "Play audio")}
                type="button"
              >
                <IconGlyph name={isPlaying ? "pause" : "play"} />
              </button>
              <button
                aria-label="Jump forward 5 seconds"
                className="top-bar__icon-button now-playing-dock__transport-button"
                onClick={() => {
                  seekRelative(5);
                }}
                title={maybeTitle(tooltipsEnabled, "Jump forward 5 seconds")}
                type="button"
              >
                <IconGlyph name="seek-forward-5" />
              </button>
              <button
                aria-label="Jump forward 30 seconds"
                className="top-bar__icon-button now-playing-dock__transport-button"
                onClick={() => {
                  seekRelative(30);
                }}
                title={maybeTitle(tooltipsEnabled, "Jump forward 30 seconds")}
                type="button"
              >
                <IconGlyph name="seek-forward-30" />
              </button>
            </div>
            <div className="now-playing-dock__speed">
              <button
                aria-label="Decrease playback speed"
                className="top-bar__icon-button now-playing-dock__speed-button"
                onClick={() => {
                  clickSpeed(-0.05);
                }}
                onPointerCancel={stopSpeedHold}
                onPointerDown={() => {
                  startSpeedHold(-0.05);
                }}
                onPointerLeave={stopSpeedHold}
                onPointerUp={stopSpeedHold}
                title={maybeTitle(tooltipsEnabled, "Decrease playback speed (hold to keep adjusting)")}
                type="button"
              >
                <IconGlyph name="backward" />
              </button>
              <span className="now-playing-dock__speed-copy">{speedLabel}</span>
              <button
                aria-label="Increase playback speed"
                className="top-bar__icon-button now-playing-dock__speed-button"
                onClick={() => {
                  clickSpeed(0.05);
                }}
                onPointerCancel={stopSpeedHold}
                onPointerDown={() => {
                  startSpeedHold(0.05);
                }}
                onPointerLeave={stopSpeedHold}
                onPointerUp={stopSpeedHold}
                title={maybeTitle(tooltipsEnabled, "Increase playback speed (hold to keep adjusting)")}
                type="button"
              >
                <IconGlyph name="forward" />
              </button>
            </div>
          </div>

          <div className="now-playing-dock__utility">
            <div className="now-playing-dock__utility-grid">
              <button
                aria-label="Mute audio"
                className="top-bar__icon-button now-playing-dock__utility-button"
                onClick={() => {
                  toggleMuted();
                }}
                title={maybeTitle(tooltipsEnabled, "Mute audio")}
                type="button"
              >
                <IconGlyph name="speaker" />
              </button>
              <button
                aria-label="Open jobs queue"
                className="top-bar__icon-button now-playing-dock__utility-button"
                onClick={() => {
                  onNavigate("/jobs");
                }}
                title={maybeTitle(tooltipsEnabled, "Open jobs queue")}
                type="button"
              >
                <IconGlyph name="queue" />
              </button>
              {variant === "dock" ? (
                <button
                  aria-label="Pop out player"
                  className="top-bar__icon-button now-playing-dock__utility-button"
                  onClick={() => {
                    window.open(
                      `/player/${activeSession.id}?popout=1`,
                      `open-choice-reader-player-${activeSession.id}`,
                      "width=820,height=280,resizable=yes",
                    );
                  }}
                  title={maybeTitle(tooltipsEnabled, "Pop out player")}
                  type="button"
                >
                  <IconGlyph name="popout" />
                </button>
              ) : (
                <button
                  aria-label="Open transport controls"
                  className="top-bar__icon-button now-playing-dock__utility-button"
                  onClick={() => {
                    onNavigate(`/reader/${activeSession.id}`);
                  }}
                  title={maybeTitle(tooltipsEnabled, "Open transport controls")}
                  type="button"
                >
                  <IconGlyph name="book" />
                </button>
              )}
              <button
                aria-label="Open current book"
                className="top-bar__icon-button now-playing-dock__utility-button"
                onClick={() => {
                  onNavigate(`/books/${activeSession.document_id}`);
                }}
                title={maybeTitle(tooltipsEnabled, "Open current book")}
                type="button"
              >
                <IconGlyph name="book" />
              </button>
            </div>
            <label className="now-playing-dock__volume" title={volumeTitle}>
              <span className="sr-only">Player volume</span>
              <input
                aria-label="Player volume"
                max="1"
                min="0"
                onChange={(event) => {
                  setVolume(Number(event.target.value));
                }}
                step="0.05"
                title={volumeTitle}
                type="range"
                value={volume}
              />
            </label>
          </div>
        </>
      ) : (
        <>
          <div className="now-playing-dock__details">
            <p className="now-playing-dock__title">Nothing playing yet</p>
            <p className="now-playing-dock__subtitle">Pick a book from the library to start listening.</p>
            <p className="now-playing-dock__voice">No active session</p>
          </div>
          <div className="now-playing-dock__cover-wrap">
            <div className="now-playing-dock__cover" aria-hidden="true">
              <IconGlyph name="book" />
            </div>
          </div>
          <div className="now-playing-dock__transport">
            <div className="now-playing-dock__transport-meta">
              <span>Ready</span>
            </div>
            <div className="now-playing-dock__transport-controls">
              <button aria-label="Jump back 30 seconds" className="top-bar__icon-button now-playing-dock__transport-button" disabled type="button">
                <IconGlyph name="seek-back-30" />
              </button>
              <button aria-label="Jump back 5 seconds" className="top-bar__icon-button now-playing-dock__transport-button" disabled type="button">
                <IconGlyph name="seek-back-5" />
              </button>
              <button
                aria-label="Play audio"
                className="top-bar__icon-button top-bar__icon-button--accent now-playing-dock__transport-button"
                disabled
                type="button"
              >
                <IconGlyph name="play" />
              </button>
              <button aria-label="Jump forward 5 seconds" className="top-bar__icon-button now-playing-dock__transport-button" disabled type="button">
                <IconGlyph name="seek-forward-5" />
              </button>
              <button aria-label="Jump forward 30 seconds" className="top-bar__icon-button now-playing-dock__transport-button" disabled type="button">
                <IconGlyph name="seek-forward-30" />
              </button>
            </div>
            <div className="now-playing-dock__speed">
              <button aria-label="Decrease playback speed" className="top-bar__icon-button now-playing-dock__speed-button" disabled type="button">
                <IconGlyph name="backward" />
              </button>
              <span className="now-playing-dock__speed-copy">1x</span>
              <button aria-label="Increase playback speed" className="top-bar__icon-button now-playing-dock__speed-button" disabled type="button">
                <IconGlyph name="forward" />
              </button>
            </div>
          </div>
          <div className="now-playing-dock__utility">
            <div className="now-playing-dock__utility-grid">
              <button
                aria-label="Open voices library"
                className="top-bar__icon-button now-playing-dock__utility-button"
                onClick={() => {
                  onNavigate("/voices");
                }}
                type="button"
              >
                <IconGlyph name="voices" />
              </button>
              <button
                aria-label="Open jobs queue"
                className="top-bar__icon-button now-playing-dock__utility-button"
                onClick={() => {
                  onNavigate("/jobs");
                }}
                type="button"
              >
                <IconGlyph name="queue" />
              </button>
            </div>
            <label className="now-playing-dock__volume" title={volumeTitle}>
              <span className="sr-only">Player volume</span>
              <input aria-label="Player volume" disabled max="1" min="0" step="0.05" title={volumeTitle} type="range" value={volume} />
            </label>
          </div>
        </>
      )}
      <audio hidden ref={bindAudioElement} />
    </div>
  );
}
