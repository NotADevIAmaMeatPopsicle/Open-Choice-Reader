import type { DocumentRecord } from "../api/types";

type LibrarySpotlightProps = {
  document: DocumentRecord;
  isStarting: boolean;
  onExport: (documentId: number) => void;
  onReadNow: (documentId: number) => void;
  onViewDetails: (documentId: number) => void;
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

export function LibrarySpotlight({
  document,
  isStarting,
  onExport,
  onReadNow,
  onViewDetails,
}: LibrarySpotlightProps) {
  return (
    <article aria-label="Selected library book" className="library-spotlight">
      <div className="library-spotlight__cover-shell">
        <img alt={`Cover for ${document.title}`} className="library-spotlight__cover" src={document.cover_url} />
      </div>
      <div className="library-spotlight__body">
        <p className="library-spotlight__eyebrow">{document.author ?? document.format.toUpperCase()}</p>
        <h3>{document.title}</h3>
        <p className="library-spotlight__summary">{document.summary ?? "Imported and ready to read."}</p>
        <ul className="library-spotlight__meta">
          <li>{formatProgress(document)}</li>
          <li>{document.total_sections ?? 0} sections</li>
          <li>{document.format.toUpperCase()}</li>
        </ul>
        <div className="library-spotlight__actions">
          <button
            className="book-card__button book-card__button--ghost"
            onClick={() => {
              onViewDetails(document.id);
            }}
            type="button"
          >
            View details
          </button>
          <button
            className="book-card__button"
            onClick={() => {
              onReadNow(document.id);
            }}
            type="button"
          >
            {isStarting ? "Starting..." : "Read now"}
          </button>
          <button
            className="book-card__button book-card__button--ghost"
            onClick={() => {
              onExport(document.id);
            }}
            type="button"
          >
            Export audiobook
          </button>
        </div>
      </div>
    </article>
  );
}
