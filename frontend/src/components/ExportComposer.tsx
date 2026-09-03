import type { VoicePresetRecord } from "../api/types";

type ExportComposerProps = {
  artifactBasename: string;
  errorMessage: string | null;
  isLoading: boolean;
  isQueueing: boolean;
  onArtifactBasenameChange: (value: string) => void;
  onGoToVoices: () => void;
  onQueue: () => void;
  onSplitChaptersChange: (checked: boolean) => void;
  onVoicePresetChange: (value: string) => void;
  premiumModelDetail: string;
  premiumModelLabel: string;
  selectedVoicePresetId: string;
  selectedExportNarratorName: string;
  splitChapters: boolean;
  voicePresets: VoicePresetRecord[];
};

export function ExportComposer({
  artifactBasename,
  errorMessage,
  isLoading,
  isQueueing,
  onArtifactBasenameChange,
  onGoToVoices,
  onQueue,
  onSplitChaptersChange,
  onVoicePresetChange,
  premiumModelDetail,
  premiumModelLabel,
  selectedVoicePresetId,
  selectedExportNarratorName,
  splitChapters,
  voicePresets,
}: ExportComposerProps) {
  const selectedVoicePreset = voicePresets.find((preset) => String(preset.id) === selectedVoicePresetId) ?? null;

  return (
    <div className="export-composer">
      <div>
        <p className="export-composer__title">Audiobook export narrator</p>
        <p className="export-composer__copy">
          Pick a saved cloned voice, decide whether to split chapters, and choose the artifact label.
        </p>
      </div>
      <div className="export-composer__summary-grid" aria-label="Export voice context">
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Default export narrator</p>
          <p className="voices-page__summary-value">{selectedExportNarratorName}</p>
          <p className="voices-page__summary-copy">Override below for this export only, or change the global default in Voices.</p>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Premium model</p>
          <p className="voices-page__summary-value">{premiumModelLabel}</p>
          <p className="voices-page__summary-copy">{premiumModelDetail}</p>
        </article>
      </div>
      {isLoading ? <p className="library-page__status-copy">Loading saved presets...</p> : null}
      {!isLoading && !errorMessage && voicePresets.length === 0 ? (
        <div className="library-page__empty-state">
          <p className="library-page__status-copy">No saved cloned voices yet. Open Voices to create the first export narrator.</p>
          <button className="book-card__button" onClick={onGoToVoices} type="button">
            Create first cloned voice
          </button>
        </div>
      ) : null}
      {!isLoading && voicePresets.length > 0 ? (
        <>
          <label className="library-page__field">
            <span>Voice preset</span>
            <select
              aria-label="Voice preset"
              onChange={(event) => {
                onVoicePresetChange(event.target.value);
              }}
              value={selectedVoicePresetId}
            >
              {voicePresets.length > 1 ? <option value="">Select a preset</option> : null}
              {voicePresets.map((preset) => (
                <option key={preset.id} value={String(preset.id)}>
                  {preset.name}
                </option>
              ))}
            </select>
          </label>
          {selectedVoicePreset ? (
            <p className="export-composer__selected-note">
              Selected export narrator: {selectedVoicePreset.name} • Premium model: {premiumModelLabel}
            </p>
          ) : null}
          <label className="library-page__field">
            <span>File label</span>
            <input
              aria-label="File label"
              onChange={(event) => {
                onArtifactBasenameChange(event.target.value);
              }}
              placeholder="Nightly export"
              type="text"
              value={artifactBasename}
            />
          </label>
          <label className="export-composer__checkbox">
            <input
              aria-label="Split by chapter"
              checked={splitChapters}
              onChange={(event) => {
                onSplitChaptersChange(event.target.checked);
              }}
              type="checkbox"
            />
            <span>Split by chapter</span>
          </label>
          <p className="library-page__status-copy">
            {splitChapters
              ? "Each chapter will download as its own WAV artifact."
              : "The export will be rendered as one merged WAV audiobook."}
          </p>
          <button
            className="book-card__button"
            disabled={!selectedVoicePresetId || isQueueing}
            onClick={onQueue}
            type="button"
          >
            {isQueueing ? "Queueing export..." : "Queue audiobook export"}
          </button>
        </>
      ) : null}
      {errorMessage ? (
        <p className="library-page__alert" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
