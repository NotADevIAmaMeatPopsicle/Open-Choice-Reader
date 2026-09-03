import type { DocumentRecord } from "../api/types";

type BookCardProps = {
  document: DocumentRecord;
  onExport?: (documentId: number) => void;
  onReadNow?: (documentId: number) => void;
  onViewDetails?: (documentId: number) => void;
};

function formatProgress(document: DocumentRecord) {
  if (document.is_finished) {
    return "Finished";
  }

  if (document.bookmark_enabled === false) {
    return "Bookmark off";
  }

  const progress = Math.round(document.progress_percent ?? 0);
  if (progress <= 0) {
    return "Ready to start";
  }

  return `${progress}% complete`;
}

export function BookCard({ document, onExport, onReadNow, onViewDetails }: BookCardProps) {
  return (
    <article className="book-card">
      <div className="book-card__cover-shell">
        <img
          alt={`Cover for ${document.title}`}
          className="book-card__cover"
          loading="lazy"
          src={document.cover_url}
        />
        <div className="book-card__progress-bar" aria-hidden="true">
          <span style={{ width: `${document.progress_percent ?? 0}%` }} />
        </div>
      </div>
      <div className="book-card__body">
        <p className="book-card__eyebrow">{document.author ?? document.format.toUpperCase()}</p>
        <h3 className="book-card__title">{document.title}</h3>
        <p className="book-card__summary">{document.summary ?? "Imported and ready to read."}</p>
        <div className="book-card__meta">
          <span>{formatProgress(document)}</span>
          <span>{document.total_sections ?? 0} sections</span>
        </div>
        <div className="book-card__actions">
          {onViewDetails ? (
            <button
              className="book-card__button book-card__button--ghost"
              onClick={() => {
                onViewDetails(document.id);
              }}
              type="button"
            >
              View details
            </button>
          ) : null}
          {onReadNow ? (
            <button
              className="book-card__button"
              onClick={() => {
                onReadNow(document.id);
              }}
              type="button"
            >
              Read now
            </button>
          ) : null}
          {onExport ? (
            <button
              className="book-card__button book-card__button--ghost"
              onClick={() => {
                onExport(document.id);
              }}
              type="button"
            >
              Export audiobook
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}
