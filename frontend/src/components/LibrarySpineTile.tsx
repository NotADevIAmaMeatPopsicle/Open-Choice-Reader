import type { DocumentRecord } from "../api/types";
import { formatLibraryProgress } from "./LibraryCoverTile";

type LibrarySpineTileProps = {
  document: DocumentRecord;
  isSelected: boolean;
  onSelect: (documentId: number) => void;
};

export function LibrarySpineTile({ document, isSelected, onSelect }: LibrarySpineTileProps) {
  const authorLabel = document.author ?? document.format.toUpperCase();

  return (
    <button
      aria-label={`Open spotlight for ${document.title} - ${authorLabel}`}
      aria-pressed={isSelected}
      className={`library-spine-tile${isSelected ? " library-spine-tile--selected" : ""}`}
      onClick={() => {
        onSelect(document.id);
      }}
      type="button"
    >
      <span className="library-spine-tile__glow" aria-hidden="true" />
      <span className="library-spine-tile__text">{`${document.title} - ${authorLabel}`}</span>
      <span className="library-spine-tile__progress">{formatLibraryProgress(document)}</span>
    </button>
  );
}
