import { useEffect, useMemo, useRef, useState } from "react";

import {
  createExportJob,
  createPlaybackSession,
  importInboxCandidate,
  listInboxCandidates,
  listVoicePresets,
  reimportDocument,
} from "../api/client";
import type { DocumentRecord, InboxCandidateRecord, VoicePresetRecord } from "../api/types";
import { ExportComposer } from "../components/ExportComposer";
import { LibraryConfirmPlayModal } from "../components/LibraryConfirmPlayModal";
import { LibraryImportPanel } from "../components/LibraryImportPanel";
import { LibraryShelfWall } from "../components/LibraryShelfWall";
import { LibrarySpotlight } from "../components/LibrarySpotlight";
import { refreshJobsCache } from "../hooks/useJobs";
import { setActivePlaybackSession } from "../hooks/usePlayer";
import { useLibrary } from "../hooks/useLibrary";
import { useSettings } from "../hooks/useSettings";
import { resolveVoiceOption } from "../utils/voices";

type LibraryPageProps = {
  onNavigate: (pathname: string) => void;
  searchTerm: string;
};

type SortMode = "recent" | "title" | "progress";
type ShelfView = "recommended" | "recent" | "all";

type SeriesMetadata = {
  key: string | null;
  volume: number | null;
};

function matchesSearch(searchTerm: string, document: DocumentRecord) {
  if (!searchTerm.trim()) {
    return true;
  }

  const haystack = `${document.title} ${document.author ?? ""} ${document.summary ?? ""}`.toLowerCase();
  return haystack.includes(searchTerm.toLowerCase());
}

function parseSeriesMetadata(title: string): SeriesMetadata {
  const match = title.match(/^(.*?)(?:\s+#|\s+Book\s+)(\d+)(?:\b|[^0-9])/i);
  if (!match) {
    return { key: null, volume: null };
  }

  return {
    key: match[1]?.trim().toLowerCase() ?? null,
    volume: Number(match[2]),
  };
}

function sortDocuments(documents: DocumentRecord[], sortMode: SortMode) {
  const sorted = [...documents];

  switch (sortMode) {
    case "title":
      sorted.sort((left, right) => left.title.localeCompare(right.title));
      break;
    case "progress":
      sorted.sort((left, right) => (right.progress_percent ?? 0) - (left.progress_percent ?? 0) || right.id - left.id);
      break;
    default:
      sorted.sort((left, right) => right.id - left.id);
      break;
  }

  return sorted;
}

function applyShelfView(documents: DocumentRecord[], shelfView: ShelfView) {
  if (shelfView === "recent") {
    return [...documents].sort((left, right) => right.id - left.id);
  }

  if (shelfView === "recommended") {
    return [...documents].sort((left, right) => {
      const leftScore =
        (left.progress_percent ?? 0) +
        (left.last_opened_at ? 15 : 0) +
        ((left.summary?.trim().length ?? 0) > 0 ? 2 : 0);
      const rightScore =
        (right.progress_percent ?? 0) +
        (right.last_opened_at ? 15 : 0) +
        ((right.summary?.trim().length ?? 0) > 0 ? 2 : 0);

      return rightScore - leftScore || right.id - left.id;
    });
  }

  return documents;
}

function collapseSeriesDocuments(documents: DocumentRecord[]) {
  const grouped = new Map<string, DocumentRecord>();
  const passthrough: DocumentRecord[] = [];

  documents.forEach((document) => {
    const metadata = parseSeriesMetadata(document.title);
    if (!metadata.key) {
      passthrough.push(document);
      return;
    }

    const existing = grouped.get(metadata.key);
    if (!existing) {
      grouped.set(metadata.key, document);
      return;
    }

    const existingMetadata = parseSeriesMetadata(existing.title);
    const existingVolume = existingMetadata.volume ?? Number.MAX_SAFE_INTEGER;
    const nextVolume = metadata.volume ?? Number.MAX_SAFE_INTEGER;

    if (nextVolume < existingVolume || (nextVolume === existingVolume && document.title.localeCompare(existing.title) < 0)) {
      grouped.set(metadata.key, document);
    }
  });

  return [...grouped.values(), ...passthrough];
}

function getPresetIdFromVoiceOptionId(voiceOptionId: string | null | undefined) {
  if (!voiceOptionId?.startsWith("preset:")) {
    return "";
  }

  return voiceOptionId.replace("preset:", "");
}

export function LibraryPage({ onNavigate, searchTerm }: LibraryPageProps) {
  const { documents, refresh } = useLibrary();
  const { settings, updateSettings, voiceOptions } = useSettings();
  const [sortMode, setSortMode] = useState<SortMode>("title");
  const [shelfView, setShelfView] = useState<ShelfView>("recommended");
  const [collapseSeries, setCollapseSeries] = useState(false);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);
  const [isStartingDocumentId, setIsStartingDocumentId] = useState<number | null>(null);
  const [activeExportDocumentId, setActiveExportDocumentId] = useState<number | null>(null);
  const [pendingReadDocument, setPendingReadDocument] = useState<DocumentRecord | null>(null);
  const [voicePresets, setVoicePresets] = useState<VoicePresetRecord[]>([]);
  const [isLoadingVoicePresets, setIsLoadingVoicePresets] = useState(false);
  const [selectedVoicePresetId, setSelectedVoicePresetId] = useState("");
  const [splitChapters, setSplitChapters] = useState(false);
  const [artifactBasename, setArtifactBasename] = useState("");
  const [exportError, setExportError] = useState<string | null>(null);
  const [isQueueingExport, setIsQueueingExport] = useState(false);
  const [isInboxOpen, setIsInboxOpen] = useState(false);
  const [isInboxLoading, setIsInboxLoading] = useState(false);
  const [inboxCandidates, setInboxCandidates] = useState<InboxCandidateRecord[]>([]);
  const [inboxError, setInboxError] = useState<string | null>(null);
  const [activeInboxPath, setActiveInboxPath] = useState<string | null>(null);
  const [inboxNotice, setInboxNotice] = useState<string | null>(null);
  const activeExportDocumentIdRef = useRef<number | null>(null);
  const presetRequestIdRef = useRef(0);
  const queueRequestIdRef = useRef(0);

  const searchedDocuments = useMemo(
    () => documents.filter((document) => matchesSearch(searchTerm, document)),
    [documents, searchTerm],
  );
  const browsedDocuments = useMemo(
    () => sortDocuments(applyShelfView(searchedDocuments, shelfView), sortMode),
    [searchedDocuments, shelfView, sortMode],
  );
  const shelfDocuments = useMemo(
    () => (collapseSeries ? collapseSeriesDocuments(browsedDocuments) : browsedDocuments),
    [browsedDocuments, collapseSeries],
  );
  const spotlightSeedId = useMemo(() => {
    const recommendedDocument = applyShelfView(searchedDocuments, "recommended")[0];
    if (recommendedDocument) {
      const visibleRecommendedDocument = shelfDocuments.find((document) => document.id === recommendedDocument.id);
      if (visibleRecommendedDocument) {
        return visibleRecommendedDocument.id;
      }
    }

    return shelfDocuments[0]?.id ?? null;
  }, [searchedDocuments, shelfDocuments]);
  const selectedDocument =
    shelfDocuments.find((document) => document.id === selectedDocumentId) ??
    shelfDocuments.find((document) => document.id === spotlightSeedId) ??
    null;
  const selectedExportVoice = resolveVoiceOption(settings?.default_export_voice_id, voiceOptions);
  const libraryViewMode = settings?.library_view_mode === "spine" ? "spine" : "cover";
  const selectedCloneModel =
    settings?.clone_runtime?.available_models?.find(
      (model) => model.engine === settings?.selected_clone_model_engine,
    ) ?? null;

  useEffect(() => {
    if (!selectedDocumentId || !shelfDocuments.some((document) => document.id === selectedDocumentId)) {
      setSelectedDocumentId(spotlightSeedId);
      return;
    }
  }, [selectedDocumentId, shelfDocuments, spotlightSeedId]);

  const loadInboxCandidates = async () => {
    setIsInboxLoading(true);
    setInboxError(null);

    try {
      setInboxCandidates(await listInboxCandidates());
    } catch (error) {
      setInboxError(error instanceof Error ? error.message : "Unable to review the server inbox");
    } finally {
      setIsInboxLoading(false);
    }
  };

  const handleStartReading = async (documentId: number) => {
    setIsStartingDocumentId(documentId);
    setPlaybackError(null);
    setInboxNotice(null);

    try {
      const session = await createPlaybackSession({ document_id: documentId });
      setActivePlaybackSession(session);
      onNavigate(`/reader/${session.id}`);
    } catch (error) {
      setPlaybackError(error instanceof Error ? error.message : "Unable to start playback");
    } finally {
      setIsStartingDocumentId(null);
    }
  };

  const handleConfirmStartReading = () => {
    if (!pendingReadDocument) {
      return;
    }

    const documentId = pendingReadDocument.id;
    setPendingReadDocument(null);
    void handleStartReading(documentId);
  };

  const handleOpenExportComposer = async (documentId: number) => {
    const requestId = presetRequestIdRef.current + 1;
    presetRequestIdRef.current = requestId;
    queueRequestIdRef.current += 1;
    activeExportDocumentIdRef.current = documentId;
    setSelectedDocumentId(documentId);
    setActiveExportDocumentId(documentId);
    setIsLoadingVoicePresets(true);
    setIsQueueingExport(false);
    setExportError(null);
    setVoicePresets([]);
    setSelectedVoicePresetId("");
    setSplitChapters(false);
    setArtifactBasename(documents.find((document) => document.id === documentId)?.title ?? "");

    try {
      const presets = await listVoicePresets();
      if (activeExportDocumentIdRef.current !== documentId || presetRequestIdRef.current !== requestId) {
        return;
      }

      setVoicePresets(presets);
      const defaultPresetId = getPresetIdFromVoiceOptionId(settings?.default_export_voice_id);
      const hasDefaultPreset = presets.some((preset) => String(preset.id) === defaultPresetId);
      setSelectedVoicePresetId(
        hasDefaultPreset ? defaultPresetId : presets.length === 1 ? String(presets[0]?.id ?? "") : "",
      );
    } catch (error) {
      if (activeExportDocumentIdRef.current !== documentId || presetRequestIdRef.current !== requestId) {
        return;
      }

      setExportError(error instanceof Error ? error.message : "Unable to load voice presets");
    } finally {
      if (activeExportDocumentIdRef.current === documentId && presetRequestIdRef.current === requestId) {
        setIsLoadingVoicePresets(false);
      }
    }
  };

  const handleQueueExport = async (documentId: number) => {
    if (!selectedVoicePresetId) {
      return;
    }

    const queueRequestId = queueRequestIdRef.current + 1;
    const voicePresetId = selectedVoicePresetId;
    queueRequestIdRef.current = queueRequestId;
    setIsQueueingExport(true);
    setExportError(null);

    try {
      await createExportJob({
        document_id: documentId,
        voice_preset_id: voicePresetId,
        clone_engine_id: settings?.selected_clone_model_engine ?? "qwen3_clone_0_6b",
        format: "wav",
        split_chapters: splitChapters,
        artifact_basename: artifactBasename.trim() || undefined,
      });

      try {
        await refreshJobsCache();
      } catch {
        // The jobs page will refetch if the cache refresh misses.
      }

      if (activeExportDocumentIdRef.current === documentId && queueRequestIdRef.current === queueRequestId) {
        onNavigate("/jobs");
      }
    } catch (error) {
      if (activeExportDocumentIdRef.current === documentId && queueRequestIdRef.current === queueRequestId) {
        setExportError(error instanceof Error ? error.message : "Unable to queue audiobook export");
      }
    } finally {
      if (activeExportDocumentIdRef.current === documentId && queueRequestIdRef.current === queueRequestId) {
        setIsQueueingExport(false);
      }
    }
  };

  const handleReviewInbox = async () => {
    const nextOpen = !isInboxOpen;
    setIsInboxOpen(nextOpen);
    setInboxNotice(null);

    if (nextOpen) {
      await loadInboxCandidates();
    }
  };

  const handleInboxAction = async (candidate: InboxCandidateRecord) => {
    setActiveInboxPath(candidate.path);
    setImportError(null);
    setPlaybackError(null);
    setInboxError(null);

    try {
      if (candidate.document_id) {
        await reimportDocument(candidate.document_id);
        setInboxNotice(`Refreshed ${candidate.name}`);
      } else {
        await importInboxCandidate(candidate.path);
        setInboxNotice(`Imported ${candidate.name}`);
      }

      await Promise.all([refresh(), loadInboxCandidates()]);
    } catch (error) {
      setInboxError(error instanceof Error ? error.message : "Unable to process inbox file");
    } finally {
      setActiveInboxPath(null);
    }
  };

  return (
    <section aria-label="Library page" className="library-page">
      <div className="library-page__hero">
        <div className="library-page__title-block">
          <p className="library-page__eyebrow">Library</p>
          <h2>Library</h2>
          <p>Browse imported titles, jump into reading, and queue audiobook exports from the same shelf-first view.</p>
        </div>
        <div className="library-page__actions">
          <button
            className="library-page__button"
            onClick={() => {
              onNavigate("/discover");
            }}
            type="button"
          >
            Discover imports
          </button>
          <button className="library-page__button library-page__button--secondary" onClick={() => void handleReviewInbox()} type="button">
            Review inbox
          </button>
        </div>
      </div>
      <div className="library-page__browse-toolbar">
        <p className="library-page__summary">{documents.length} items imported</p>
        <p className="library-page__books-count">{shelfDocuments.length} Books</p>
        <label className="library-page__toggle">
          <input
            aria-label="Collapse series"
            checked={collapseSeries}
            onChange={(event) => {
              setCollapseSeries(event.target.checked);
            }}
            type="checkbox"
          />
          <span>Collapse series</span>
        </label>
        <label className="library-page__sort">
          <span className="sr-only">Shelf view</span>
          <select
            aria-label="Shelf view"
            onChange={(event) => {
              setShelfView(event.target.value as ShelfView);
            }}
            value={shelfView}
          >
            <option value="recommended">Recommended</option>
            <option value="recent">Recent</option>
            <option value="all">All books</option>
          </select>
        </label>
        <label className="library-page__sort">
          <span className="sr-only">Sort library</span>
          <select
            aria-label="Sort library"
            onChange={(event) => {
              setSortMode(event.target.value as SortMode);
            }}
            value={sortMode}
          >
            <option value="title">Title</option>
            <option value="recent">Recently added</option>
            <option value="progress">Progress</option>
          </select>
        </label>
        <div aria-label="Shelf display mode" className="library-page__display-toggle" role="group">
          <button
            aria-pressed={libraryViewMode === "cover"}
            className={`library-page__display-button${libraryViewMode === "cover" ? " library-page__display-button--active" : ""}`}
            onClick={() => {
              void updateSettings({ library_view_mode: "cover" });
            }}
            type="button"
          >
            Face-out covers
          </button>
          <button
            aria-pressed={libraryViewMode === "spine"}
            className={`library-page__display-button${libraryViewMode === "spine" ? " library-page__display-button--active" : ""}`}
            onClick={() => {
              void updateSettings({ library_view_mode: "spine" });
            }}
            type="button"
          >
            Spines-out shelf
          </button>
        </div>
      </div>
      {isInboxOpen ? (
        <LibraryImportPanel
          activePath={activeInboxPath}
          candidates={inboxCandidates}
          isLoading={isInboxLoading}
          notice={inboxNotice}
          onCandidateAction={(candidate) => {
            void handleInboxAction(candidate);
          }}
          onRefresh={() => {
            void loadInboxCandidates();
          }}
        />
      ) : null}
      {importError ? (
        <p className="library-page__alert" role="alert">
          {importError}
        </p>
      ) : null}
      {!importError && playbackError ? (
        <p className="library-page__alert" role="alert">
          {playbackError}
        </p>
      ) : null}
      {!importError && !playbackError && inboxError ? (
        <p className="library-page__alert" role="alert">
          {inboxError}
        </p>
      ) : null}
      {pendingReadDocument ? (
        <LibraryConfirmPlayModal
          document={pendingReadDocument}
          onCancel={() => {
            setPendingReadDocument(null);
          }}
          onConfirm={handleConfirmStartReading}
        />
      ) : null}
      {selectedDocument ? (
        <>
          <LibraryShelfWall
            documents={shelfDocuments}
            onSelect={setSelectedDocumentId}
            selectedDocumentId={selectedDocument.id}
            viewMode={libraryViewMode}
          />
          <div className="library-page__spotlight-stack">
            <LibrarySpotlight
              document={selectedDocument}
              isStarting={isStartingDocumentId === selectedDocument.id}
              onExport={(documentId) => {
                void handleOpenExportComposer(documentId);
              }}
              onReadNow={(documentId) => {
                const nextDocument = shelfDocuments.find((document) => document.id === documentId);
                if (!nextDocument) {
                  return;
                }

                setPendingReadDocument(nextDocument);
              }}
              onViewDetails={(documentId) => {
                onNavigate(`/books/${documentId}`);
              }}
            />
            {activeExportDocumentId === selectedDocument.id ? (
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
                  void handleQueueExport(selectedDocument.id);
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
          </div>
        </>
      ) : (
        <div className="library-page__empty-state">
          <p>{searchTerm ? "No books match that search yet." : "Open Discover or review the watched inbox to start building the library."}</p>
        </div>
      )}
    </section>
  );
}
