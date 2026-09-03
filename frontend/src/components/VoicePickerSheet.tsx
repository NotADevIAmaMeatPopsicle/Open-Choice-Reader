import type { VoiceOptionRecord } from "../api/types";
import { resolveVoiceCapabilityLabel } from "../utils/voices";

type VoicePickerSheetProps = {
  errorMessage: string | null;
  isLoading: boolean;
  onChange: (voiceOptionId: string) => void;
  onManageVoices: () => void;
  options: VoiceOptionRecord[];
  selectedVoiceId: string;
};

export function VoicePickerSheet({
  errorMessage,
  isLoading,
  onChange,
  onManageVoices,
  options,
  selectedVoiceId,
}: VoicePickerSheetProps) {
  const selectedVoice = options.find((option) => option.id === selectedVoiceId) ?? options[0] ?? null;
  const groupedOptions = options.reduce<Record<string, VoiceOptionRecord[]>>((groups, option) => {
    const family = option.engine_family ?? option.engine;
    groups[family] = groups[family] ? [...groups[family], option] : [option];
    return groups;
  }, {});

  return (
    <section aria-label="Live voice selection" className="voice-picker-sheet">
      <div className="voice-picker-sheet__header">
        <div>
          <p className="book-page__eyebrow">Narrator</p>
          <h3>Live reading voice</h3>
          <p>
            Choose a live-capable narrator for instant playback. Saved cloned voices can join live reading when the clone runtime
            is available.
          </p>
        </div>
        <button className="book-card__button book-card__button--ghost" onClick={onManageVoices} type="button">
          Manage voices
        </button>
      </div>
      <div className="voice-picker-sheet__current">
        <p className="voice-picker-sheet__label">Current narrator</p>
        {selectedVoice ? (
          <>
            <p className="voice-picker-sheet__name">{selectedVoice.name}</p>
            <p className="voice-picker-sheet__detail">
              Engine: {selectedVoice.engine_family ?? selectedVoice.engine} | {selectedVoice.mode_label} |{" "}
              {resolveVoiceCapabilityLabel(selectedVoice)}
            </p>
            <p className="voice-picker-sheet__detail">
              {selectedVoice.model_name ?? "Built-in narrator"} | {selectedVoice.availability_detail}
            </p>
          </>
        ) : (
          <p className="voice-picker-sheet__detail">No live reader voice is available on this host yet.</p>
        )}
      </div>
      <label className="book-page__field">
        <span>Live reading voice</span>
        <select
          aria-label="Live reading voice"
          disabled={isLoading || options.length === 0}
          onChange={(event) => {
            onChange(event.target.value);
          }}
          value={selectedVoiceId}
        >
          {options.length === 0 ? <option value="">No live voices available</option> : null}
          {Object.entries(groupedOptions).map(([family, familyOptions]) => (
            <optgroup key={family} label={`${family.toUpperCase()} narrators`}>
              {familyOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name} | {resolveVoiceCapabilityLabel(option)}
                  {option.availability !== "available" ? " | unavailable on this host" : ""}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      <p className="voice-picker-sheet__supporting-copy">
        Global defaults and the premium clone model live in Voices. If a cloned preset is unavailable here, keep it
        selected and check the host/runtime note for the reason.
      </p>
      {errorMessage ? (
        <p className="library-page__alert" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </section>
  );
}
