import { useState } from "react";

import type { DocumentRecord } from "../api/types";

type LibraryCoverTileProps = {
  document: DocumentRecord;
  isSelected: boolean;
  onSelect: (documentId: number) => void;
};

export function coverFallbackHue(title: string) {
  let hash = 0;
  for (const character of title) {
    hash = (hash * 31 + character.charCodeAt(0)) % 360;
  }
  return hash;
}

export function formatLibraryProgress(document: DocumentRecord) {
  if (document.is_finished) {
    return "Finished";
  }

  if (document.bookmark_enabled === false) {
    return "Bookmark off";
  }

  const progress = Math.round(document.progress_percent ?? 0);
  if (progress <= 0) {
    return "Ready";
  }

  return `${progress}%`;
}

export function LibraryCoverTile({ document, isSelected, onSelect }: LibraryCoverTileProps) {
  const [coverFailed, setCoverFailed] = useState(false);
  const fallbackHue = coverFallbackHue(document.title);

  return (
    <button
      aria-label={`Open spotlight for ${document.title}`}
      aria-pressed={isSelected}
      className={`library-cover-tile${isSelected ? " library-cover-tile--selected" : ""}`}
      onClick={() => {
        onSelect(document.id);
      }}
      type="button"
    >
      <span className="library-cover-tile__cover-shell">
        {coverFailed || !document.cover_url ? (
          <span
            aria-hidden="true"
            className="library-cover-tile__cover library-cover-tile__cover--fallback"
            style={{
              background: `linear-gradient(165deg, hsl(${fallbackHue} 36% 34%), hsl(${fallbackHue} 44% 16%))`,
            }}
          >
            <span className="library-cover-tile__fallback-title">{document.title}</span>
            <span className="library-cover-tile__fallback-author">
              {document.author ?? document.format.toUpperCase()}
            </span>
          </span>
        ) : (
          <img
            alt={`Cover for ${document.title}`}
            className="library-cover-tile__cover"
            loading="lazy"
            onError={() => {
              setCoverFailed(true);
            }}
            src={document.cover_url}
          />
        )}
        <span className="library-cover-tile__spine" aria-hidden="true" />
      </span>
      <span className="library-cover-tile__caption">
        <span className="library-cover-tile__title">{document.title}</span>
        <span className="library-cover-tile__meta">
          {document.author ?? document.format.toUpperCase()} | {formatLibraryProgress(document)}
        </span>
      </span>
    </button>
  );
}
