import type { VoiceOptionRecord } from "../api/types";

type ReaderControlsDrawerProps = {
  errorMessage: string | null;
  isLoading: boolean;
  onPlaybackSpeedChange: (speed: number) => void;
  onVoiceChange: (voiceOptionId: string) => void;
  playbackSpeed: number;
  selectedVoiceId: string;
  voiceOptions: VoiceOptionRecord[];
};

export function ReaderControlsDrawer({
  errorMessage,
  isLoading,
  onPlaybackSpeedChange,
  onVoiceChange,
  playbackSpeed,
  selectedVoiceId,
  voiceOptions,
}: ReaderControlsDrawerProps) {
  const selectedVoice = voiceOptions.find((voiceOption) => voiceOption.id === selectedVoiceId) ?? voiceOptions[0] ?? null;
  const groupedVoiceOptions = voiceOptions.reduce<Record<string, VoiceOptionRecord[]>>((groups, voiceOption) => {
    const family = voiceOption.engine_family ?? voiceOption.engine;
    groups[family] = groups[family] ? [...groups[family], voiceOption] : [voiceOption];
    return groups;
  }, {});

  return (
    <aside aria-label="Reader controls" className="reader-controls-drawer">
      <div className="reader-controls-drawer__header">
        <p className="reader-controls-drawer__eyebrow">Reader controls</p>
        <h3>Voice and speed</h3>
        <p>Adjust the live reading voice and playback pace without leaving the current session.</p>
      </div>
      <div className="reader-controls-drawer__fields">
        <label className="book-page__field">
          <span>Playback speed</span>
          <input
            aria-label="Playback speed"
            max="8"
            min="0.5"
            onChange={(event) => {
              onPlaybackSpeedChange(Number(event.target.value));
            }}
            step="0.05"
            type="number"
            value={Number(playbackSpeed.toFixed(2))}
          />
        </label>
        <label className="book-page__field">
          <span>Live reading voice</span>
          <select
            aria-label="Live reading voice"
            disabled={isLoading || voiceOptions.length === 0}
            onChange={(event) => {
              onVoiceChange(event.target.value);
            }}
            value={selectedVoiceId}
          >
            {voiceOptions.length === 0 ? <option value="">No live voices available</option> : null}
            {Object.entries(groupedVoiceOptions).map(([family, familyOptions]) => (
              <optgroup key={family} label={`${family.toUpperCase()} narrators`}>
                {familyOptions.map((voiceOption) => (
                  <option key={voiceOption.id} value={voiceOption.id}>
                    {voiceOption.name} | {voiceOption.mode_label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        {selectedVoice ? (
          <p className="reader-controls-drawer__voice-note">
            Narrator: {selectedVoice.name} | Engine: {selectedVoice.engine_family ?? selectedVoice.engine} |{" "}
            {selectedVoice.model_name ?? "Built-in narrator"} | {selectedVoice.availability_detail}
          </p>
        ) : null}
      </div>
      {errorMessage ? (
        <p className="library-page__alert" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </aside>
  );
}
