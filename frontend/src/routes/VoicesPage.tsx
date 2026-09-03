import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import { fetchVoicePreviewAudio, importCloneSample, searchCloneSamples, transcribeReferenceAudio } from "../api/client";
import type { CloneSampleCandidateRecord, VoiceOptionRecord } from "../api/types";
import { EngineVoiceGroup } from "../components/EngineVoiceGroup";
import { ModelChoiceCard } from "../components/ModelChoiceCard";
import { ShareWithFriend } from "../components/ShareWithFriend";
import { useSettings } from "../hooks/useSettings";
import { useVoices } from "../hooks/useVoices";
import { resolveVoiceCapabilityLabel } from "../utils/voices";

function transcriptPreview(value: string | null) {
  if (!value) {
    return "No transcript saved.";
  }

  if (value.length <= 120) {
    return value;
  }

  return `${value.slice(0, 117)}...`;
}

export function VoicesPage() {
  const {
    builtInVoices,
    clonedVoiceOptions,
    createError,
    createPreset,
    isCreating,
    isLoading,
    loadError,
    refresh,
    voiceOptions,
    voicePresets,
  } = useVoices();
  const {
    error: settingsError,
    isLoading: isLoadingSettings,
    isSaving,
    saveSuccessMessage,
    settings,
    updateSettings,
  } = useSettings();
  const [name, setName] = useState("");
  const [transcript, setTranscript] = useState("");
  const [referenceAudio, setReferenceAudio] = useState<File | null>(null);
  const [defaultLiveVoiceId, setDefaultLiveVoiceId] = useState("");
  const [defaultExportVoiceId, setDefaultExportVoiceId] = useState("");
  const [fallbackVoiceId, setFallbackVoiceId] = useState("");
  const [selectedCloneModelEngine, setSelectedCloneModelEngine] = useState("qwen3_clone_0_6b");
  const [sampleSearchQuery, setSampleSearchQuery] = useState("");
  const [sampleResults, setSampleResults] = useState<CloneSampleCandidateRecord[]>([]);
  const [selectedSample, setSelectedSample] = useState<CloneSampleCandidateRecord | null>(null);
  const [reviewedSampleTranscript, setReviewedSampleTranscript] = useState("");
  const [sampleSearchError, setSampleSearchError] = useState<string | null>(null);
  const [sampleSearchMessage, setSampleSearchMessage] = useState<string | null>(null);
  const [isSearchingSamples, setIsSearchingSamples] = useState(false);
  const [isImportingSample, setIsImportingSample] = useState(false);
  const [transcriptionError, setTranscriptionError] = useState<string | null>(null);
  const [transcriptionMessage, setTranscriptionMessage] = useState<string | null>(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewMessage, setPreviewMessage] = useState<string | null>(null);
  const [previewingVoiceId, setPreviewingVoiceId] = useState<string | null>(null);
  const nameInputRef = useRef<HTMLInputElement | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  const previewUrlRef = useRef<string | null>(null);

  const stopPreview = () => {
    if (previewAudioRef.current) {
      previewAudioRef.current.pause();
      previewAudioRef.current.currentTime = 0;
      previewAudioRef.current.src = "";
      previewAudioRef.current = null;
    }

    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current);
      previewUrlRef.current = null;
    }

    setPreviewingVoiceId(null);
  };

  useEffect(() => {
    if (!settings) {
      return;
    }

    setDefaultLiveVoiceId(settings.default_live_voice_id);
    setDefaultExportVoiceId(settings.default_export_voice_id);
    setFallbackVoiceId(settings.fallback_voice_id ?? "");
    setSelectedCloneModelEngine(settings.selected_clone_model_engine ?? "qwen3_clone_0_6b");
  }, [settings]);

  useEffect(() => {
    return () => {
      stopPreview();
    };
  }, []);

  const builtInVoiceGroups = useMemo(() => {
    return builtInVoices.reduce<Record<string, typeof builtInVoices>>((groups, voice) => {
      const family = voice.engine_family ?? voice.engine;
      groups[family] = groups[family] ? [...groups[family], voice] : [voice];
      return groups;
    }, {});
  }, [builtInVoices]);

  const allVoiceOptions = useMemo(() => [...voiceOptions], [voiceOptions]);
  const cloneRuntimeModels = settings?.clone_runtime?.available_models ?? [];
  const selectedLiveVoice = allVoiceOptions.find((voice) => voice.id === defaultLiveVoiceId) ?? null;
  const selectedFallbackVoice = allVoiceOptions.find((voice) => voice.id === fallbackVoiceId) ?? null;
  const selectedExportVoice = allVoiceOptions.find((voice) => voice.id === defaultExportVoiceId) ?? null;
  const selectedCloneModel = cloneRuntimeModels.find((model) => model.engine === selectedCloneModelEngine) ?? null;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;

    if (!referenceAudio) {
      return;
    }

    const wasCreated = await createPreset(name, transcript, referenceAudio);
    if (!wasCreated) {
      return;
    }

    setName("");
    setTranscript("");
    setReferenceAudio(null);
    form.reset();
  };

  const handleSaveDefaults = async () => {
    if (!settings) {
      return;
    }

    await updateSettings({
      default_export_voice_id: defaultExportVoiceId || settings.default_export_voice_id,
      default_live_voice_id: defaultLiveVoiceId || settings.default_live_voice_id,
      fallback_voice_id: fallbackVoiceId || null,
      selected_clone_model_engine: selectedCloneModelEngine,
    });
  };

  const handleTranscribeReference = async () => {
    if (!referenceAudio) {
      return;
    }

    setIsTranscribing(true);
    setTranscriptionError(null);
    setTranscriptionMessage("Transcribing reference audio locally...");

    try {
      const result = await transcribeReferenceAudio(referenceAudio);
      setTranscript(result.transcript);
      setTranscriptionMessage("Transcript draft is ready to review.");
    } catch (error) {
      setTranscriptionMessage(null);
      setTranscriptionError(error instanceof Error ? error.message : "Unable to transcribe reference audio");
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleSampleSearch = async () => {
    setIsSearchingSamples(true);
    setSampleSearchError(null);
    setSampleSearchMessage(null);

    try {
      const result = await searchCloneSamples(sampleSearchQuery, 10);
      setSampleResults(result.items);
      setSelectedSample(result.items[0] ?? null);
      setReviewedSampleTranscript(result.items[0]?.transcript ?? "");
      setSampleSearchMessage(result.items.length === 0 ? "No matching samples found." : null);
    } catch (error) {
      setSampleSearchError(error instanceof Error ? error.message : "Unable to search public voice samples");
    } finally {
      setIsSearchingSamples(false);
    }
  };

  const handleImportSample = async () => {
    if (!selectedSample || !reviewedSampleTranscript.trim()) {
      return;
    }

    setIsImportingSample(true);
    setSampleSearchError(null);
    setSampleSearchMessage(null);

    try {
      await importCloneSample({
        provider: selectedSample.provider,
        title: selectedSample.title,
        speaker: selectedSample.speaker,
        audio_url: selectedSample.audio_url,
        transcript: reviewedSampleTranscript,
        transcript_source_url: selectedSample.transcript_source_url,
        source_url: selectedSample.source_url,
        license_label: selectedSample.license_label,
        provenance_note: selectedSample.provenance_note,
      });
      await refresh();
      setSampleSearchMessage("Reviewed sample imported into cloned voices.");
    } catch (error) {
      setSampleSearchError(error instanceof Error ? error.message : "Unable to import reviewed sample");
    } finally {
      setIsImportingSample(false);
    }
  };

  const builtInVoiceCountLabel = `${builtInVoices.length} built-in reader voices`;
  const clonedPresetCountLabel = `${voicePresets.length} cloned presets`;

  const handlePreviewVoice = async (voice: VoiceOptionRecord) => {
    if (!voice.supports_live_reading || voice.availability !== "available") {
      return;
    }

    if (previewingVoiceId === voice.id) {
      stopPreview();
      setPreviewMessage(null);
      return;
    }

    setPreviewError(null);
    stopPreview();
    setPreviewingVoiceId(voice.id);
    setPreviewMessage(
      `Previewing ${voice.name} on ${voice.mode_label}${voice.model_name ? ` | ${voice.model_name}` : ""}`,
    );

    try {
      const previewBlob = await fetchVoicePreviewAudio(voice.id);
      const previewUrl = URL.createObjectURL(previewBlob);
      const audio = new Audio(previewUrl);
      previewUrlRef.current = previewUrl;
      previewAudioRef.current = audio;
      audio.addEventListener("ended", () => {
        stopPreview();
        setPreviewMessage(null);
      });
      await audio.play();
    } catch (error) {
      stopPreview();
      setPreviewMessage(null);
      setPreviewError(error instanceof Error ? error.message : "Unable to preview narrator");
    }
  };

  return (
    <section aria-label="Voices page" className="voices-page">
      <div className="voices-page__header">
        <div className="voices-page__title-block">
          <h2>Voices</h2>
          <p>Choose the live narrator, fallback narrator, export narrator, and premium clone model from one place.</p>
        </div>
        <button className="voices-page__button" disabled={!settings || isSaving} onClick={() => void handleSaveDefaults()} type="button">
          {isSaving ? "Saving voice defaults..." : "Save voice defaults"}
        </button>
      </div>

      {saveSuccessMessage ? <p className="library-page__status-copy">{saveSuccessMessage}</p> : null}
      {previewMessage ? <p className="library-page__status-copy">{previewMessage}</p> : null}

      <section className="voices-page__defaults-strip" aria-label="Current defaults">
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Default live narrator</p>
          <p className="voices-page__summary-value">{selectedLiveVoice?.name ?? "Not selected"}</p>
          <p className="voices-page__summary-copy">{selectedLiveVoice?.engine_family ?? selectedLiveVoice?.engine ?? "No live engine selected"}</p>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Fallback live narrator</p>
          <p className="voices-page__summary-value">{selectedFallbackVoice?.name ?? "No automatic fallback"}</p>
          <p className="voices-page__summary-copy">{selectedFallbackVoice?.engine_family ?? "Fallback disabled"}</p>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Default export narrator</p>
          <p className="voices-page__summary-value">{selectedExportVoice?.name ?? "Not selected"}</p>
          <p className="voices-page__summary-copy">{selectedExportVoice?.mode_label ?? "Choose a cloned preset or export-capable narrator"}</p>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Premium clone model</p>
          <p className="voices-page__summary-value">{selectedCloneModel?.display_name ?? "Premium clone 0.6B"}</p>
          <p className="voices-page__summary-copy">{selectedCloneModel?.model_name ?? settings?.clone_runtime?.model_name ?? "Model unavailable"}</p>
        </article>
      </section>

      <div className="voices-page__summary-grid">
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Built-in voices</p>
          <p className="voices-page__summary-value">{builtInVoiceCountLabel}</p>
          <p className="voices-page__summary-copy">Live-reading narrators grouped by engine family so the best reading voice is easy to choose quickly.</p>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Cloned voices</p>
          <p className="voices-page__summary-value">{clonedPresetCountLabel}</p>
          <p className="voices-page__summary-copy">Saved premium narrators for live reading and audiobook export.</p>
        </article>
      </div>

      <section className="voices-page__panel" aria-label="Built-in voices section">
        <div className="voices-page__section-header">
          <div>
            <h3>Built-in narrator shelves</h3>
            <p>Pick the live-reading default and fallback from the installed voice families.</p>
          </div>
        </div>
        {builtInVoices.length === 0 ? (
          <div className="voices-page__empty-state">
            <p>No built-in reader voices are available on this host right now.</p>
            <p>Open Settings to confirm server runtime status, then return here to set the live defaults.</p>
          </div>
        ) : (
          <div className="voices-page__engine-groups">
            <EngineVoiceGroup
              fallbackVoiceId={fallbackVoiceId}
              liveVoiceId={defaultLiveVoiceId}
              onSetFallbackVoice={setFallbackVoiceId}
              onSetLiveVoice={setDefaultLiveVoiceId}
              onPreviewVoice={(voice) => {
                void handlePreviewVoice(voice);
              }}
              previewingVoiceId={previewingVoiceId}
              title="Kokoro narrators"
              voices={builtInVoiceGroups.kokoro ?? []}
            />
            <EngineVoiceGroup
              fallbackVoiceId={fallbackVoiceId}
              liveVoiceId={defaultLiveVoiceId}
              onSetFallbackVoice={setFallbackVoiceId}
              onSetLiveVoice={setDefaultLiveVoiceId}
              onPreviewVoice={(voice) => {
                void handlePreviewVoice(voice);
              }}
              previewingVoiceId={previewingVoiceId}
              title="Piper narrators"
              voices={builtInVoiceGroups.piper ?? []}
            />
          </div>
        )}
      </section>

      <section className="voices-page__panel" aria-label="Cloned voices section">
        <div className="voices-page__section-header">
          <div>
            <h3>Cloned narrators</h3>
            <p>Saved cloned presets can be used for live reading and audiobook export when the clone runtime is ready.</p>
          </div>
          <button
            className="book-card__button book-card__button--ghost"
            onClick={() => {
              nameInputRef.current?.focus();
            }}
            type="button"
          >
            {voicePresets.length === 0 ? "Create first cloned voice" : "Clone another voice"}
          </button>
        </div>
        {isLoading || isLoadingSettings ? <p className="voices-page__section-copy">Loading saved presets and runtime details...</p> : null}
        {!isLoading && !createError && !loadError && voicePresets.length === 0 ? (
          <div className="voices-page__empty-state">
            <p>No cloned voices saved yet. Upload a reference clip below to create the first cloned narrator.</p>
            <p>Once a preset is saved, you can set it as the live default, the export default, or both.</p>
          </div>
        ) : null}
        {voicePresets.length > 0 ? (
          <ul aria-label="Saved voice presets" className="voices-page__cards voices-page__preset-list">
            {voicePresets.map((preset) => {
              const voiceOption = clonedVoiceOptions.find((option) => option.id === `preset:${preset.id}`);
              const presetVoiceId = `preset:${preset.id}`;
              const isLiveDefault = defaultLiveVoiceId === presetVoiceId;
              const isExportDefault = defaultExportVoiceId === presetVoiceId;
              const isPreviewing = previewingVoiceId === presetVoiceId;
              const previewDisabled =
                !voiceOption || !voiceOption.supports_live_reading || voiceOption.availability !== "available";

              return (
                <li className="voices-page__voice-card" key={preset.id}>
                  <div className="voices-page__voice-card-header">
                    <div>
                      <p className="voices-page__voice-name">{preset.name}</p>
                      <p className="voices-page__voice-copy">{transcriptPreview(preset.transcript)}</p>
                    </div>
                    <span className="voices-page__voice-chip">{voiceOption?.mode_label ?? preset.engine}</span>
                  </div>
                  <p className="voices-page__voice-copy">{resolveVoiceCapabilityLabel(voiceOption)} • {voiceOption?.model_name ?? "Premium clone model"}</p>
                  <p className="voices-page__voice-copy">
                    {voiceOption?.availability_detail ?? "Saved preset is ready to use when the clone runtime is available."}
                  </p>
                  <div className="engine-voice-group__actions">
                    <button
                      aria-label={`Preview narrator ${preset.name}`}
                      className="book-card__button book-card__button--ghost"
                      disabled={previewDisabled}
                      onClick={() => {
                        if (voiceOption) {
                          void handlePreviewVoice(voiceOption);
                        }
                      }}
                      type="button"
                    >
                      {isPreviewing ? "Previewing..." : "Preview narrator"}
                    </button>
                    <button
                      className={isLiveDefault ? "book-card__button" : "book-card__button book-card__button--ghost"}
                      onClick={() => {
                        setDefaultLiveVoiceId(presetVoiceId);
                      }}
                      type="button"
                    >
                      {isLiveDefault ? "Live default" : "Set as live default"}
                    </button>
                    <button
                      className={isExportDefault ? "book-card__button" : "book-card__button book-card__button--ghost"}
                      onClick={() => {
                        setDefaultExportVoiceId(presetVoiceId);
                      }}
                      type="button"
                    >
                      {isExportDefault ? "Export default" : "Set as export default"}
                    </button>
                  </div>
                  <ShareWithFriend itemId={preset.id} itemLabel={preset.name} itemType="voice_preset" />
                </li>
              );
            })}
          </ul>
        ) : null}
      </section>

      <section className="voices-page__panel" aria-label="Premium clone model section">
        <div className="voices-page__section-header">
          <div>
            <h3>Premium clone model</h3>
            <p>Choose the clone model to use with saved cloned presets for live reading and export.</p>
          </div>
        </div>
        <div className="voices-page__model-grid">
          {cloneRuntimeModels.map((model) => (
            <ModelChoiceCard
              availabilityDetail={model.availability_detail}
              displayName={model.display_name}
              isSelected={selectedCloneModelEngine === model.engine}
              key={model.engine}
              modelName={model.model_name}
              onSelect={() => {
                setSelectedCloneModelEngine(model.engine);
              }}
              usageHint={
                model.engine === "qwen3_clone_1_7b"
                  ? "Higher-quality render for premium live reading and audiobook export."
                  : "Faster render for cloned live reading and shorter export queue time."
              }
            />
          ))}
        </div>
        {cloneRuntimeModels.length === 0 ? (
          <div className="voices-page__empty-state">
            <p>No premium clone models are reported by this host yet.</p>
            <p>Open Settings to confirm server runtime status, then return here to choose the export model.</p>
          </div>
        ) : null}
      </section>

      <section className="voices-page__panel" aria-label="Public clone sample search">
        <div className="voices-page__section-header">
          <div>
            <h3>Find public voice samples</h3>
            <p>Search public-domain sample sources, review the transcript, then import the clip into your cloned voice presets.</p>
          </div>
        </div>
        <label className="library-page__field">
          <span>Search public voice samples</span>
          <input
            aria-label="Search public voice samples"
            onChange={(event) => {
              setSampleSearchQuery(event.target.value);
            }}
            type="search"
            value={sampleSearchQuery}
          />
        </label>
        <button
          className="book-card__button"
          disabled={isSearchingSamples || !sampleSearchQuery.trim()}
          onClick={() => {
            void handleSampleSearch();
          }}
          type="button"
        >
          {isSearchingSamples ? "Searching samples..." : "Search samples"}
        </button>
        {sampleResults.length > 0 ? (
          <div className="voices-page__cards voices-page__sample-results">
            {sampleResults.map((sample) => (
              <article className="voices-page__voice-card" key={sample.id}>
                <div className="voices-page__voice-card-header">
                  <div>
                    <button
                      className="book-card__button book-card__button--ghost voices-page__sample-title"
                      onClick={() => {
                        setSelectedSample(sample);
                        setReviewedSampleTranscript(sample.transcript ?? "");
                      }}
                      type="button"
                    >
                      {sample.title}
                    </button>
                    <p className="voices-page__voice-copy">
                      {sample.provider} | {sample.license_label}
                    </p>
                  </div>
                  <span className="voices-page__voice-chip">{sample.speaker ?? "Public sample"}</span>
                </div>
                <p className="voices-page__voice-copy">{sample.provenance_note}</p>
                <p className="voices-page__voice-copy voices-page__source-links">
                  <a href={sample.source_url}>Source</a>
                  <a href={sample.transcript_source_url}>Transcript source</a>
                </p>
              </article>
            ))}
          </div>
        ) : null}
        {selectedSample ? (
          <div className="voices-page__form voices-page__review-form">
            <label className="library-page__field">
              <span>Reviewed transcript</span>
              <textarea
                aria-label="Reviewed transcript"
                onChange={(event) => {
                  setReviewedSampleTranscript(event.target.value);
                }}
                rows={4}
                value={reviewedSampleTranscript}
              />
            </label>
            <button
              className="book-card__button"
              disabled={isImportingSample || !reviewedSampleTranscript.trim()}
              onClick={() => {
                void handleImportSample();
              }}
              type="button"
            >
              {isImportingSample ? "Importing sample..." : "Import reviewed sample"}
            </button>
          </div>
        ) : null}
        {sampleSearchMessage ? <p className="library-page__status-copy">{sampleSearchMessage}</p> : null}
        {sampleSearchError ? (
          <p className="library-page__alert" role="alert">
            {sampleSearchError}
          </p>
        ) : null}
      </section>

      <section className="voices-page__panel voices-page__form-panel" aria-label="Clone voice form">
        <div className="voices-page__section-header">
          <div>
            <h3>Clone a new voice</h3>
            <p>Upload a short reference clip and matching transcript to save a reusable cloned narrator for live reading and export.</p>
          </div>
        </div>
        <form
          className="voices-page__form"
          onSubmit={(event) => {
            void handleSubmit(event);
          }}
        >
          <label className="library-page__field">
            <span>Display name</span>
            <input
              aria-label="Display name"
              onChange={(event) => {
                setName(event.target.value);
              }}
              ref={nameInputRef}
              type="text"
              value={name}
            />
          </label>
          <label className="library-page__field">
            <span>Transcript</span>
            <textarea
              aria-label="Transcript"
              onChange={(event) => {
                setTranscript(event.target.value);
              }}
              rows={4}
              value={transcript}
            />
          </label>
          <label className="library-page__field">
            <span>Reference audio file</span>
            <input
              accept="audio/*"
              aria-label="Reference audio file"
              onChange={(event: ChangeEvent<HTMLInputElement>) => {
                setReferenceAudio(event.target.files?.[0] ?? null);
                setTranscriptionError(null);
                setTranscriptionMessage(null);
              }}
              type="file"
            />
          </label>
          <button
            className="book-card__button book-card__button--ghost"
            disabled={isTranscribing || Boolean(transcriptionMessage) || !referenceAudio}
            onClick={() => {
              void handleTranscribeReference();
            }}
            type="button"
          >
            {isTranscribing ? "Transcribing audio..." : "Transcribe audio"}
          </button>
          {transcriptionMessage ? <p className="library-page__status-copy">{transcriptionMessage}</p> : null}
          {transcriptionError ? (
            <p className="library-page__alert" role="alert">
              {transcriptionError}
            </p>
          ) : null}
          <button className="voices-page__button" disabled={isCreating || !referenceAudio} type="submit">
            {isCreating ? "Saving preset..." : "Save cloned voice"}
          </button>
        </form>
      </section>

      {createError ? (
        <p role="alert" style={{ margin: "0 0 1rem", color: "#ffb4ab" }}>
          {createError}
        </p>
      ) : null}
      {!createError && loadError ? (
        <p role="alert" style={{ margin: "0 0 1rem", color: "#ffb4ab" }}>
          {loadError}
        </p>
      ) : null}
      {!createError && !loadError && settingsError ? (
        <p role="alert" style={{ margin: "0 0 1rem", color: "#ffb4ab" }}>
          {settingsError}
        </p>
      ) : null}
      {!createError && !loadError && !settingsError && previewError ? (
        <p role="alert" style={{ margin: "0 0 1rem", color: "#ffb4ab" }}>
          {previewError}
        </p>
      ) : null}
    </section>
  );
}
