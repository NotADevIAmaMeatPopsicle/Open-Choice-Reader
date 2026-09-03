import type { ReactNode } from "react";

import type { DocumentRecord } from "../api/types";

type BookHeroProps = {
  canReadNow: boolean;
  document: DocumentRecord;
  exportActionLabel: string;
  isExportDisabled: boolean;
  isStartingPlayback: boolean;
  liveVoiceControl: ReactNode;
  onBack: () => void;
  onExport: () => void;
  onReadNow: () => void;
  statusSummary: string;
};

function formatProgress(document: DocumentRecord) {
  if (document.is_finished) {
    return "Finished";
  }

  if (document.bookmark_enabled === false) {
    return "Bookmark off";
  }

  return `${Math.round(document.progress_percent ?? 0)}% complete`;
}

export function BookHero({
  canReadNow,
  document,
  exportActionLabel,
  isExportDisabled,
  isStartingPlayback,
  liveVoiceControl,
  onBack,
  onExport,
  onReadNow,
  statusSummary,
}: BookHeroProps) {
  return (
    <section className="book-hero" aria-label="Book overview">
      <div className="book-hero__cover-shell">
        <img alt={`Cover for ${document.title}`} className="book-hero__cover" src={document.cover_url} />
      </div>
      <div className="book-hero__body">
        <div className="book-hero__copy">
          <p className="book-page__eyebrow">Document {document.id}</p>
          <h2>{document.title}</h2>
          <p>{statusSummary}</p>
          {document.summary ? <p className="book-hero__summary">{document.summary}</p> : null}
        </div>
        <ul className="book-page__meta" aria-label="Document details">
          <li>{document.author ?? `${document.format?.toUpperCase?.() ?? "Imported"} document`}</li>
          <li>{document.total_sections ?? 0} sections</li>
          <li>{formatProgress(document)}</li>
        </ul>
        {liveVoiceControl}
        <div className="book-page__actions">
          <button className="library-page__button library-page__button--secondary" onClick={onBack} type="button">
            Back to library
          </button>
          <button
            className="library-page__button"
            disabled={!canReadNow || isStartingPlayback}
            onClick={onReadNow}
            type="button"
          >
            {isStartingPlayback ? "Starting..." : "Read now"}
          </button>
          <button
            className="library-page__button"
            disabled={isExportDisabled}
            onClick={onExport}
            type="button"
          >
            {exportActionLabel}
          </button>
        </div>
      </div>
    </section>
  );
}
