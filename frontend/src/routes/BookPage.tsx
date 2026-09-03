import { useEffect, useMemo, useRef, useState } from "react";

import {
  clearDocumentFinished,
  createExportJob,
  createPlaybackSession,
  deleteDocument,
  getDocumentDetail,
  listVoicePresets,
  markDocumentFinished,
  resetDocumentBookmark,
  updateDocumentBookmark,
} from "../api/client";
import type { DocumentDetailRecord, DocumentRecord, VoicePresetRecord } from "../api/types";
import { ExportComposer } from "../components/ExportComposer";
import { BookHero } from "../components/BookHero";
import { ChapterList } from "../components/ChapterList";
import { ShareWithFriend } from "../components/ShareWithFriend";
import { VoicePickerSheet } from "../components/VoicePickerSheet";
import { refreshJobsCache } from "../hooks/useJobs";
import { setActivePlaybackSession } from "../hooks/usePlayer";
import { useLibrary } from "../hooks/useLibrary";
import { useSettings } from "../hooks/useSettings";
import { resolveVoiceCapabilityLabel, resolveVoiceEngineName, resolveVoiceOption } from "../utils/voices";

type BookPageProps = {
  bookId: string;
  onNavigate: (pathname: string) => void;
};

function getDocumentSummary(document: DocumentRecord) {
  switch (document.status) {
    case "processing":
      return "Still preparing for playback";
    case "failed":
      return "Import needs attention before playback";
    default:
      return hasActionableDocumentStatus(document.status)
        ? "Ready to read or export"
        : "Imported and waiting for final processing";
  }
}

function hasActionableDocumentStatus(status: DocumentRecord["status"]) {
  return status !== "processing" && status !== "failed";
}

function isDocumentDetailRecord(value: unknown): value is DocumentDetailRecord {
  return typeof value === "object" && value !== null && "id" in value && "title" in value;
}

function getPresetIdFromVoiceOptionId(voiceOptionId: string | null | undefined) {
  if (!voiceOptionId?.startsWith("preset:")) {
    return "";
  }

  return voiceOptionId.replace("preset:", "");
}

function formatImportModeLabel(importMode: string | null | undefined) {
  switch (importMode) {
    case "article_url":
      return "Article import";
    case "direct_url":
      return "Direct URL import";
    case "pasted_text":
      return "Pasted text";
    default:
      return "Catalog or local import";
  }
}

function hasSavedBookmark(document: DocumentRecord | DocumentDetailRecord) {
  return document.current_chunk_index != null && document.last_opened_at != null;
}

function getReadingStateSummary(document: DocumentRecord | DocumentDetailRecord) {
  if (document.is_finished) {
    return "Finished";
  }

  if (document.bookmark_enabled === false) {
    return "Bookmark off";
  }

  if (hasSavedBookmark(document)) {
    return `Resume saved at ${Math.round(document.progress_percent ?? 0)}% complete`;
  }

  return "No saved bookmark yet";
}

export function BookPage({ bookId, onNavigate }: BookPageProps) {
  const { documents, isLoading, refresh } = useLibrary();
  const {
    error: voiceLoadError,
    isLoading: isLoadingVoiceSettings,
    settings,
    voiceOptions,
  } = useSettings();
  const [documentDetail, setDocumentDetail] = useState<DocumentDetailRecord | null>(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [stateActionError, setStateActionError] = useState<string | null>(null);
  const [isStartingPlayback, setIsStartingPlayback] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isUpdatingDocumentState, setIsUpdatingDocumentState] = useState(false);
  const [isExportComposerOpen, setIsExportComposerOpen] = useState(false);
  const [isLoadingVoicePresets, setIsLoadingVoicePresets] = useState(false);
  const [isQueueingExport, setIsQueueingExport] = useState(false);
  const [voicePresets, setVoicePresets] = useState<VoicePresetRecord[]>([]);
  const [selectedVoicePresetId, setSelectedVoicePresetId] = useState("");
  const [splitChapters, setSplitChapters] = useState(false);
  const [artifactBasename, setArtifactBasename] = useState("");
  const [selectedLiveVoiceId, setSelectedLiveVoiceId] = useState("");
  const activeDocumentIdRef = useRef<number | null>(null);
  const detailRequestIdRef = useRef(0);
  const isQueueingExportRef = useRef(false);
  const presetRequestIdRef = useRef(0);
  const queueRequestIdRef = useRef(0);

  const documentId = Number(bookId);
  const document = documents.find((candidate) => candidate.id === documentId);
  const mergedDocument = documentDetail ?? document;
  const canStartDocumentActions = mergedDocument ? hasActionableDocumentStatus(mergedDocument.status) : false;
  const liveVoiceOptions = useMemo(
    () => voiceOptions.filter((voiceOption) => voiceOption.supports_live_reading),
    [voiceOptions],
  );
  const selectedLiveVoice = liveVoiceOptions.find((voiceOption) => voiceOption.id === selectedLiveVoiceId) ?? null;
  const selectedExportVoice = resolveVoiceOption(settings?.default_export_voice_id, voiceOptions);
  const selectedCloneModel =
    settings?.clone_runtime?.available_models?.find(
      (model) => model.engine === settings?.selected_clone_model_engine,
    ) ?? null;
  const canStartReading =
    canStartDocumentActions &&
    (liveVoiceOptions.length === 0 || selectedLiveVoice == null || selectedLiveVoice.availability === "available");
  const savedBookmarkAvailable = mergedDocument ? hasSavedBookmark(mergedDocument) : false;

  useEffect(() => {
    if (!Number.isFinite(documentId) || documentId <= 0) {
      setDocumentDetail(null);
      setDetailError(null);
      return;
    }

    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;
    activeDocumentIdRef.current = documentId;
    setIsLoadingDetail(true);
    setDetailError(null);

    void getDocumentDetail(documentId)
      .then((detail) => {
        if (activeDocumentIdRef.current !== documentId || detailRequestIdRef.current !== requestId) {
          return;
        }

        if (!isDocumentDetailRecord(detail)) {
          throw new Error("Unable to load book detail");
        }

        setDocumentDetail(detail);
      })
      .catch((error) => {
        if (activeDocumentIdRef.current !== documentId || detailRequestIdRef.current !== requestId) {
          return;
        }

        setDetailError(error instanceof Error ? error.message : "Unable to load book detail");
      })
      .finally(() => {
        if (activeDocumentIdRef.current === documentId && detailRequestIdRef.current === requestId) {
          setIsLoadingDetail(false);
        }
      });
  }, [documentId]);

  useEffect(() => {
    if (liveVoiceOptions.length === 0) {
      setSelectedLiveVoiceId("");
      return;
    }

    const defaultLiveVoiceId = settings?.default_live_voice_id ?? liveVoiceOptions[0]?.id ?? "";
    const selectionStillExists = liveVoiceOptions.some((voiceOption) => voiceOption.id === selectedLiveVoiceId);
    if (!selectedLiveVoiceId || !selectionStillExists) {
      setSelectedLiveVoiceId(defaultLiveVoiceId);
    }
  }, [liveVoiceOptions, selectedLiveVoiceId, settings?.default_live_voice_id]);

  const handleStartReading = async (startSectionId?: number) => {
    if (!mergedDocument) {
      return;
    }

    setIsStartingPlayback(true);
    setPlaybackError(null);

    try {
      const session = await createPlaybackSession({
        document_id: mergedDocument.id,
        start_section_id: startSectionId,
        voice_option_id: selectedLiveVoiceId || settings?.default_live_voice_id,
      });
      setActivePlaybackSession(session);
      onNavigate(`/reader/${session.id}`);
    } catch (error) {
      setPlaybackError(error instanceof Error ? error.message : "Unable to start playback");
    } finally {
      setIsStartingPlayback(false);
    }
  };

  const handleOpenExportComposer = async () => {
    if (!mergedDocument || isQueueingExportRef.current) {
      return;
    }

    const requestId = presetRequestIdRef.current + 1;
    presetRequestIdRef.current = requestId;
    activeDocumentIdRef.current = mergedDocument.id;
    setIsExportComposerOpen(true);
    setVoicePresets([]);
    setSelectedVoicePresetId("");
    setSplitChapters(false);
    setArtifactBasename(mergedDocument.title);
    setIsLoadingVoicePresets(true);
    setExportError(null);

    try {
      const presets = await listVoicePresets();
      if (activeDocumentIdRef.current !== mergedDocument.id || presetRequestIdRef.current !== requestId) {
        return;
      }

      setVoicePresets(presets);
      const defaultPresetId = getPresetIdFromVoiceOptionId(settings?.default_export_voice_id);
      const hasDefaultPreset = presets.some((preset) => String(preset.id) === defaultPresetId);
      setSelectedVoicePresetId(
        hasDefaultPreset ? defaultPresetId : presets.length === 1 ? String(presets[0]?.id ?? "") : "",
      );
    } catch (error) {
      if (activeDocumentIdRef.current !== mergedDocument.id || presetRequestIdRef.current !== requestId) {
        return;
      }

      setExportError(error instanceof Error ? error.message : "Unable to load voice presets");
    } finally {
      if (activeDocumentIdRef.current === mergedDocument.id && presetRequestIdRef.current === requestId) {
        setIsLoadingVoicePresets(false);
      }
    }
  };

  const handleQueueExport = async () => {
    if (!mergedDocument || !selectedVoicePresetId || isQueueingExportRef.current) {
      return;
    }

    const requestId = queueRequestIdRef.current + 1;
    queueRequestIdRef.current = requestId;
    isQueueingExportRef.current = true;
    setIsQueueingExport(true);
    setExportError(null);

    try {
      await createExportJob({
        document_id: mergedDocument.id,
        voice_preset_id: selectedVoicePresetId,
        clone_engine_id: settings?.selected_clone_model_engine ?? "qwen3_clone_0_6b",
        format: "wav",
        split_chapters: splitChapters,
        artifact_basename: artifactBasename.trim() || undefined,
      });

      try {
        await refreshJobsCache();
      } catch {
        // The jobs route can refetch if the warm cache misses.
      }

      if (activeDocumentIdRef.current === mergedDocument.id && queueRequestIdRef.current === requestId) {
        onNavigate("/jobs");
      }
    } catch (error) {
      if (activeDocumentIdRef.current === mergedDocument.id && queueRequestIdRef.current === requestId) {
        setExportError(error instanceof Error ? error.message : "Unable to queue audiobook export");
      }
    } finally {
      if (activeDocumentIdRef.current === mergedDocument.id && queueRequestIdRef.current === requestId) {
        isQueueingExportRef.current = false;
        setIsQueueingExport(false);
      }
    }
  };

  const syncUpdatedDocument = async (updatedDocument: DocumentRecord) => {
    setDocumentDetail((currentDetail) =>
      currentDetail && currentDetail.id === updatedDocument.id ? { ...currentDetail, ...updatedDocument } : currentDetail,
    );
    await refresh();
  };

  const handleToggleBookmark = async (enabled: boolean) => {
    if (!mergedDocument) {
      return;
    }

    setIsUpdatingDocumentState(true);
    setStateActionError(null);

    try {
      const updatedDocument = await updateDocumentBookmark(mergedDocument.id, enabled);
      await syncUpdatedDocument(updatedDocument);
    } catch (error) {
      setStateActionError(error instanceof Error ? error.message : "Unable to update bookmark preference");
    } finally {
      setIsUpdatingDocumentState(false);
    }
  };

  const handleResetBookmark = async () => {
    if (!mergedDocument) {
      return;
    }

    setIsUpdatingDocumentState(true);
    setStateActionError(null);

    try {
      const updatedDocument = await resetDocumentBookmark(mergedDocument.id);
      await syncUpdatedDocument(updatedDocument);
    } catch (error) {
      setStateActionError(error instanceof Error ? error.message : "Unable to reset bookmark");
    } finally {
      setIsUpdatingDocumentState(false);
    }
  };

  const handleToggleFinished = async () => {
    if (!mergedDocument) {
      return;
    }

    setIsUpdatingDocumentState(true);
    setStateActionError(null);

    try {
      const updatedDocument = mergedDocument.is_finished
        ? await clearDocumentFinished(mergedDocument.id)
        : await markDocumentFinished(mergedDocument.id);
      await syncUpdatedDocument(updatedDocument);
    } catch (error) {
      setStateActionError(error instanceof Error ? error.message : "Unable to update finished state");
    } finally {
      setIsUpdatingDocumentState(false);
    }
  };

  const handleDeleteDocument = async () => {
    if (!mergedDocument) {
      return;
    }

    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteDocument(mergedDocument.id);
      setActivePlaybackSession(null);
      onNavigate("/");
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "Unable to remove this book");
      setIsDeleting(false);
      setIsConfirmingDelete(false);
    }
  };

  if (isLoading && documents.length === 0) {
    return (
      <section aria-label="Book details page" className="library-page">
        <div className="library-page__title-block">
          <h2>Loading document</h2>
          <p>Fetching the latest library details for this title.</p>
        </div>
      </section>
    );
  }

  if (!mergedDocument) {
    if (isLoadingDetail) {
      return (
        <section aria-label="Book details page" className="library-page">
          <div className="library-page__title-block">
            <h2>Loading document</h2>
            <p>Fetching the latest book detail for this title.</p>
          </div>
        </section>
      );
    }

    return (
      <section aria-label="Book details page" className="library-page">
        <div className="library-page__title-block">
          <h2>Document unavailable</h2>
          <p>We couldn't load the library details for this document right now.</p>
        </div>
        <div className="book-page__actions">
          <button
            className="library-page__button library-page__button--secondary"
            onClick={() => {
              onNavigate("/");
            }}
            type="button"
          >
            Back to library
          </button>
        </div>
      </section>
    );
  }

  return (
    <section aria-label="Book details page" className="library-page book-page">
      <BookHero
        canReadNow={canStartReading}
        document={mergedDocument}
        exportActionLabel={isLoadingVoicePresets ? "Loading presets..." : "Export audiobook"}
        isExportDisabled={!canStartDocumentActions || isLoadingVoicePresets || isQueueingExport}
        isStartingPlayback={isStartingPlayback}
        liveVoiceControl={
          <VoicePickerSheet
            errorMessage={voiceLoadError}
            isLoading={isLoadingVoiceSettings}
            onChange={setSelectedLiveVoiceId}
            onManageVoices={() => {
              onNavigate("/voices");
            }}
            options={liveVoiceOptions}
            selectedVoiceId={selectedLiveVoiceId}
          />
        }
        onBack={() => {
          onNavigate("/");
        }}
        onExport={() => {
          void handleOpenExportComposer();
        }}
        onReadNow={() => {
          void handleStartReading();
        }}
        statusSummary={getDocumentSummary(mergedDocument)}
      />

      {!canStartDocumentActions ? (
        <p className="book-page__supporting-copy">
          This document needs to finish processing before playback or export can begin.
        </p>
      ) : null}

      {canStartDocumentActions && selectedLiveVoice && selectedLiveVoice.availability !== "available" ? (
        <p className="book-page__supporting-copy">
          Live reading will unlock once the selected voice is available on this host.
        </p>
      ) : null}

      <section className="voices-page__summary-grid" aria-label="Book voice context">
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Current narrator</p>
          <p className="voices-page__summary-value">{selectedLiveVoice?.name ?? "Not selected"}</p>
          <p className="voices-page__summary-copy">
            Engine: {resolveVoiceEngineName(selectedLiveVoiceId, liveVoiceOptions)}
            {selectedLiveVoice?.model_name ? ` • ${selectedLiveVoice.model_name}` : ""}
            {selectedLiveVoice ? ` • ${resolveVoiceCapabilityLabel(selectedLiveVoice)}` : ""}
          </p>
          <p className="voices-page__summary-copy">
            {selectedLiveVoice?.availability_detail ?? "Narrator availability details are unavailable right now."}
          </p>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Export narrator</p>
          <p className="voices-page__summary-value">{selectedExportVoice?.name ?? "Not selected"}</p>
          <p className="voices-page__summary-copy">
            Premium model: {selectedCloneModel?.display_name ?? "Premium clone 0.6B"}
          </p>
        </article>
      </section>

      <section className="voices-page__summary-grid" aria-label="Reading state controls">
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Reading state</p>
          <p className="voices-page__summary-value">{getReadingStateSummary(mergedDocument)}</p>
          <p className="voices-page__summary-copy">
            {mergedDocument.is_finished
              ? "This title is marked finished and no longer appears in Continue Reading."
              : mergedDocument.bookmark_enabled === false
                ? "Resume tracking is disabled for this title until you turn it back on."
                : savedBookmarkAvailable
                  ? "Your place will be restored automatically the next time you open this title."
                  : "Open the title and progress will be remembered automatically once bookmark tracking is enabled."}
          </p>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Reader actions</p>
          <p className="voices-page__summary-value">Manage progress memory</p>
          <div className="book-page__actions book-page__actions--stacked">
            <button
              className="library-page__button library-page__button--secondary"
              disabled={!savedBookmarkAvailable || isUpdatingDocumentState}
              onClick={() => {
                void handleResetBookmark();
              }}
              type="button"
            >
              {isUpdatingDocumentState ? "Updating..." : "Reset bookmark"}
            </button>
            <button
              className="library-page__button library-page__button--secondary"
              disabled={isUpdatingDocumentState}
              onClick={() => {
                void handleToggleBookmark(mergedDocument.bookmark_enabled === false);
              }}
              type="button"
            >
              {mergedDocument.bookmark_enabled === false ? "Enable bookmark" : "Disable bookmark"}
            </button>
            <button
              className="library-page__button library-page__button--secondary"
              disabled={isUpdatingDocumentState}
              onClick={() => {
                void handleToggleFinished();
              }}
              type="button"
            >
              {mergedDocument.is_finished ? "Mark unfinished" : "Mark finished"}
            </button>
          </div>
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Share</p>
          <p className="voices-page__summary-value">Send a copy to a friend</p>
          <ShareWithFriend itemId={mergedDocument.id} itemLabel={mergedDocument.title} itemType="document" />
        </article>
        <article className="voices-page__summary-card">
          <p className="voices-page__summary-label">Remove</p>
          <p className="voices-page__summary-value">Take this book out of your library</p>
          <p className="voices-page__summary-copy">
            Removes the book, its reading history, and finished exports. Copies you shared with friends are
            not affected.
          </p>
          <button
            className="book-card__button book-card__button--danger"
            disabled={isDeleting}
            onClick={() => {
              setDeleteError(null);
              setIsConfirmingDelete(true);
            }}
            type="button"
          >
            Remove from library
          </button>
          {deleteError ? (
            <p className="library-page__alert" role="alert">
              {deleteError}
            </p>
          ) : null}
        </article>
      </section>

      {isConfirmingDelete ? (
        <div className="library-page__modal-backdrop">
          <div aria-label="Confirm removal" aria-modal="true" className="library-page__modal" role="dialog">
            <div className="library-page__modal-copy">
              <h3>Remove from library</h3>
              <p>{`Permanently remove "${mergedDocument.title}" and its reading history?`}</p>
            </div>
            <div className="library-page__modal-actions">
              <button
                className="book-card__button book-card__button--danger"
                disabled={isDeleting}
                onClick={() => {
                  void handleDeleteDocument();
                }}
                type="button"
              >
                {isDeleting ? "Removing..." : "Remove book"}
              </button>
              <button
                className="book-card__button book-card__button--ghost"
                disabled={isDeleting}
                onClick={() => {
                  setIsConfirmingDelete(false);
                }}
                type="button"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {mergedDocument.source_provider_name || mergedDocument.source_site_name || mergedDocument.source_url || mergedDocument.import_mode ? (
        <section className="voices-page__summary-grid" aria-label="Import provenance">
          <article className="voices-page__summary-card">
            <p className="voices-page__summary-label">Import type</p>
            <p className="voices-page__summary-value">{formatImportModeLabel(mergedDocument.import_mode)}</p>
            <p className="voices-page__summary-copy">
              {mergedDocument.source_provider_name ?? "Imported directly into the library"}
            </p>
          </article>
          <article className="voices-page__summary-card">
            <p className="voices-page__summary-label">Source</p>
            <p className="voices-page__summary-value">{mergedDocument.source_site_name ?? mergedDocument.source_provider_name ?? "Local file"}</p>
            <p className="voices-page__summary-copy">
              {mergedDocument.source_url ? (
                <a className="jobs-page__download-link" href={mergedDocument.source_url} rel="noreferrer" target="_blank">
                  {mergedDocument.source_url}
                </a>
              ) : (
                mergedDocument.source_provider_url ?? "No external source URL saved for this item."
              )}
            </p>
          </article>
        </section>
      ) : null}

      {detailError ? (
        <p className="library-page__alert" role="alert">
          {detailError}
        </p>
      ) : null}

      {playbackError ? (
        <p className="library-page__alert" role="alert">
          {playbackError}
        </p>
      ) : null}

      {stateActionError ? (
        <p className="library-page__alert" role="alert">
          {stateActionError}
        </p>
      ) : null}

      {isLoadingDetail ? <p className="book-page__supporting-copy">Loading chapters...</p> : null}

      {documentDetail?.sections?.length ? (
        <ChapterList
          currentChunkIndex={documentDetail.current_chunk_index}
          isStartingPlayback={isStartingPlayback}
          onReadFromSection={(sectionId) => {
            void handleStartReading(sectionId);
          }}
          sections={documentDetail.sections}
        />
      ) : (
        <section className="chapter-list" aria-label="Chapters">
          <div className="chapter-list__header">
            <h3>Chapters</h3>
            <p>No chapter markers are available for this document yet.</p>
          </div>
        </section>
      )}

      {isExportComposerOpen ? (
        <ExportComposer
          artifactBasename={artifactBasename}
          errorMessage={exportError}
          isLoading={isLoadingVoicePresets}
          isQueueing={isQueueingExport}
          onArtifactBasenameChange={setArtifactBasename}
          onGoToVoices={() => {
            onNavigate("/voices");
          }}
          onQueue={() => {
            void handleQueueExport();
          }}
          premiumModelDetail={selectedCloneModel?.model_name ?? settings?.clone_runtime?.model_name ?? "Model unavailable"}
          premiumModelLabel={selectedCloneModel?.display_name ?? "Premium clone 0.6B"}
          selectedExportNarratorName={selectedExportVoice?.name ?? "No default export narrator selected"}
          onSplitChaptersChange={setSplitChapters}
          onVoicePresetChange={setSelectedVoicePresetId}
          selectedVoicePresetId={selectedVoicePresetId}
          splitChapters={splitChapters}
          voicePresets={voicePresets}
        />
      ) : null}
    </section>
  );
}
