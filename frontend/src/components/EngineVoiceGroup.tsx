import type { VoiceOptionRecord } from "../api/types";
import { resolveVoiceCapabilityLabel } from "../utils/voices";

type EngineVoiceGroupProps = {
  fallbackVoiceId: string;
  liveVoiceId: string;
  onSetFallbackVoice: (voiceId: string) => void;
  onSetLiveVoice: (voiceId: string) => void;
  onPreviewVoice: (voice: VoiceOptionRecord) => void;
  previewingVoiceId: string | null;
  title: string;
  voices: VoiceOptionRecord[];
};

export function EngineVoiceGroup({
  fallbackVoiceId,
  liveVoiceId,
  onSetFallbackVoice,
  onSetLiveVoice,
  onPreviewVoice,
  previewingVoiceId,
  title,
  voices,
}: EngineVoiceGroupProps) {
  if (voices.length === 0) {
    return null;
  }

  return (
    <section className="engine-voice-group" aria-label={title}>
      <div className="engine-voice-group__header">
        <div>
          <h4>{title}</h4>
          <p>{voices[0]?.mode_label ?? "Narrator group"}</p>
        </div>
        <span className="engine-voice-group__count">{voices.length} voices</span>
      </div>
      <div className="engine-voice-group__grid">
        {voices.map((voice) => {
          const isLiveDefault = liveVoiceId === voice.id;
          const isFallback = fallbackVoiceId === voice.id;
          const isPreviewing = previewingVoiceId === voice.id;
          const previewDisabled = !voice.supports_live_reading || voice.availability !== "available";

          return (
            <article className="engine-voice-group__card" key={voice.id}>
              <div className="engine-voice-group__card-header">
                <div>
                  <p className="engine-voice-group__name">{voice.name}</p>
                  <p className="engine-voice-group__detail">{voice.description}</p>
                </div>
                <span className="engine-voice-group__chip">{voice.engine_family ?? voice.engine}</span>
              </div>
              <p className="engine-voice-group__availability">{resolveVoiceCapabilityLabel(voice)}</p>
              <p className="engine-voice-group__availability">{voice.availability_detail}</p>
              <div className="engine-voice-group__actions">
                <button
                  aria-label={`Preview narrator ${voice.name}`}
                  className="book-card__button book-card__button--ghost"
                  disabled={previewDisabled}
                  onClick={() => {
                    onPreviewVoice(voice);
                  }}
                  type="button"
                >
                  {isPreviewing ? "Previewing..." : "Preview narrator"}
                </button>
                <button
                  className={isLiveDefault ? "book-card__button" : "book-card__button book-card__button--ghost"}
                  onClick={() => {
                    onSetLiveVoice(voice.id);
                  }}
                  type="button"
                >
                  {isLiveDefault ? "Live default" : "Set as live default"}
                </button>
                <button
                  className={isFallback ? "book-card__button" : "book-card__button book-card__button--ghost"}
                  onClick={() => {
                    onSetFallbackVoice(voice.id);
                  }}
                  type="button"
                >
                  {isFallback ? "Fallback" : "Set as fallback"}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
