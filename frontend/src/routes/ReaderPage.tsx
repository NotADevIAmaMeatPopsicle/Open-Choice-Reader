import { ReaderControlsDrawer } from "../components/ReaderControlsDrawer";
import { ReaderTextPane } from "../components/ReaderTextPane";
import { TransportBar } from "../components/TransportBar";
import { useReader } from "../hooks/useReader";
import {
  resolveVoiceCapabilityLabel,
  resolveVoiceEngineName,
  resolveVoiceName,
  resolveVoiceOption,
} from "../utils/voices";

type ReaderPageProps = {
  sessionId: string;
};

export function ReaderPage({ sessionId }: ReaderPageProps) {
  const {
    activeSession,
    advanceProgress,
    currentChunkIndex,
    error,
    isHydrating,
    isPlaying,
    isVoiceSettingsLoading,
    liveVoiceOptions,
    playbackSpeed,
    prebufferError,
    prebufferStatus,
    seekRelative,
    sectionChunks,
    selectedVoiceId,
    sessionTitle,
    togglePlayback,
    updateProgressIndex,
    updatePlaybackSpeed,
    updateVoiceOption,
    voiceSettingsError,
  } = useReader({
    sessionId,
  });
  const selectedVoiceName = resolveVoiceName(selectedVoiceId, liveVoiceOptions);
  const selectedVoice = resolveVoiceOption(selectedVoiceId, liveVoiceOptions);
  const selectedVoiceEngine = resolveVoiceEngineName(selectedVoiceId, liveVoiceOptions);

  if (isHydrating && !activeSession) {
    return (
      <section aria-label="Reader page" className="reader-page">
        <div className="reader-page__hero">
          <p className="reader-page__eyebrow">Reader</p>
          <h2>Reading progress</h2>
          <p>Loading session {sessionId} from the local host.</p>
        </div>
      </section>
    );
  }

  if (!activeSession) {
    return (
      <section aria-label="Reader page" className="reader-page">
        <div className="reader-page__hero">
          <p className="reader-page__eyebrow">Reader</p>
          <h2>Reading progress</h2>
          <p>{error ?? "This reading session is not available right now."}</p>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Reader page" className="reader-page">
      <div className="reader-page__hero">
        <div className="reader-page__title-block">
          <p className="reader-page__eyebrow">Reader</p>
          <h2>Reading progress</h2>
          <p>{sessionTitle}</p>
        </div>
        <p className="reader-page__summary">
          Narrator: {selectedVoiceName} | Engine: {selectedVoiceEngine} |{" "}
          {playbackSpeed.toFixed(playbackSpeed % 1 === 0 ? 0 : 2).replace(/0+$/, "").replace(/\.$/, "")}x playback
          with synced local progress.
        </p>
        <p className="reader-page__summary">
          {activeSession.voice_model_name ?? selectedVoice?.model_name ?? "Built-in narrator"} |{" "}
          {resolveVoiceCapabilityLabel(selectedVoice)} | {selectedVoice?.availability_detail ?? "Narrator details unavailable"}
        </p>
      </div>
      {error ? (
        <p className="library-page__alert" role="alert">
          {error}
        </p>
      ) : null}
      {prebufferStatus === "preparing" || prebufferStatus === "prepared" ? (
        <p className="library-page__status-copy">Cloned voice is readying the next chunk.</p>
      ) : null}
      {prebufferError ? (
        <p className="library-page__alert" role="alert">
          {prebufferError}
        </p>
      ) : null}
      <div className="reader-page__grid">
        <ReaderTextPane
          currentChunkIndex={currentChunkIndex}
          currentSectionTitle={activeSession.current_section_title}
          sectionChunks={sectionChunks}
        />
        <ReaderControlsDrawer
          errorMessage={voiceSettingsError}
          isLoading={isVoiceSettingsLoading}
          onPlaybackSpeedChange={(nextSpeed) => {
            void updatePlaybackSpeed(nextSpeed);
          }}
          onVoiceChange={(voiceOptionId) => {
            void updateVoiceOption(voiceOptionId);
          }}
          playbackSpeed={playbackSpeed}
          selectedVoiceId={selectedVoiceId}
          voiceOptions={liveVoiceOptions}
        />
      </div>
      <TransportBar
        currentChunkIndex={currentChunkIndex}
        isPlaying={isPlaying}
        onAdvanceProgress={() => {
          void advanceProgress();
        }}
        onProgressChange={(nextChunkIndex) => {
          void updateProgressIndex(nextChunkIndex);
        }}
        onSeekRelative={(seconds) => {
          seekRelative(seconds);
        }}
        onTogglePlayback={() => {
          void togglePlayback();
        }}
        totalChunks={activeSession.total_chunks}
      />
    </section>
  );
}
